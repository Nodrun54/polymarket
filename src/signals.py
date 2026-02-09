"""
Trading signals module for Polymarket Trading Bot.
Aggregates 11 indicators into BULLISH/BEARISH/NEUTRAL signals with confidence.
"""
from dataclasses import dataclass
from typing import Optional
from . import config
from . import indicators
from .feeds import State


@dataclass
class Signal:
    """Trading signal with direction and confidence."""
    direction: str  # "BULLISH", "BEARISH", "NEUTRAL"
    confidence: int  # 1-10
    details: dict  # Individual indicator values
    rsi_trigger: bool = False  # True if RSI triggered the signal (for aggressive profit booking)
    
    @property
    def should_trade(self) -> bool:
        """Returns True if confidence meets threshold."""
        return (
            self.direction != "NEUTRAL" and 
            self.confidence >= config.SIGNAL_CONFIDENCE_THRESHOLD
        )
    
    @property
    def action(self) -> Optional[str]:
        """Returns 'BUY_UP', 'BUY_DOWN', or None."""
        if not self.should_trade:
            return None
        return "BUY_UP" if self.direction == "BULLISH" else "BUY_DOWN"


def calculate_signal(state: State) -> Signal:
    """
    Calculate trading signal from all indicators.
    
    Scoring system:
    - Each indicator contributes -1, 0, or +1 to the score
    - Final score is normalized to direction + confidence
    """
    details = {}
    bullish_points = 0
    bearish_points = 0
    total_indicators = 0
    
    # ═══════════════════════════════════════════════════════════════════════
    # ORDER BOOK INDICATORS
    # ═══════════════════════════════════════════════════════════════════════
    
    # 1. OBI (Order Book Imbalance)
    if state.bids and state.asks and state.mid > 0:
        obi_val = indicators.obi(state.bids, state.asks, state.mid)
        details["obi"] = obi_val
        total_indicators += 1
        if obi_val > config.OBI_THRESH:
            bullish_points += 1
        elif obi_val < -config.OBI_THRESH:
            bearish_points += 1
    
    # 2. Buy/Sell Walls
    if state.bids and state.asks:
        buy_walls, sell_walls = indicators.walls(state.bids, state.asks)
        details["buy_walls"] = len(buy_walls)
        details["sell_walls"] = len(sell_walls)
        total_indicators += 1
        if len(buy_walls) > len(sell_walls):
            bullish_points += 1
        elif len(sell_walls) > len(buy_walls):
            bearish_points += 1
    
    # 3. Liquidity Depth (use 0.5% band)
    if state.bids and state.asks and state.mid > 0:
        depth = indicators.depth_usd(state.bids, state.asks, state.mid)
        details["depth_0.5pct"] = depth.get(0.5, 0)
        # Depth is informational, doesn't contribute to direction
    
    # ═══════════════════════════════════════════════════════════════════════
    # FLOW INDICATORS
    # ═══════════════════════════════════════════════════════════════════════
    
    # 4-6. CVD (1m, 3m, 5m)
    for window in config.CVD_WINDOWS:
        if state.trades:
            cvd_val = indicators.cvd(state.trades, window)
            details[f"cvd_{window}s"] = cvd_val
            total_indicators += 1
            if cvd_val > 0:
                bullish_points += 1
            elif cvd_val < 0:
                bearish_points += 1
    
    # 7. Delta (1m)
    if state.trades:
        delta_val = indicators.delta(state.trades)
        details["delta_1m"] = delta_val
        total_indicators += 1
        if delta_val > 0:
            bullish_points += 1
        elif delta_val < 0:
            bearish_points += 1
    
    # 8. Volume Profile (POC)
    if state.klines:
        poc, _ = indicators.vol_profile(state.klines)
        details["poc"] = poc
        if state.mid > 0:
            total_indicators += 1
            if state.mid > poc:
                bullish_points += 1
            elif state.mid < poc:
                bearish_points += 1
    
    # ═══════════════════════════════════════════════════════════════════════
    # TECHNICAL ANALYSIS INDICATORS
    # ═══════════════════════════════════════════════════════════════════════
    
    # 9. RSI - Enhanced for aggressive low RSI buy strategy
    rsi_trigger = False
    if state.klines:
        rsi_val = indicators.rsi(state.klines)
        if rsi_val is not None:
            details["rsi"] = rsi_val
            total_indicators += 1
            
            # Extreme oversold (RSI < 25) = Strong buy signal with bonus points
            if rsi_val < 25:
                bullish_points += 3  # Triple weight for extreme oversold
                rsi_trigger = True
                details["rsi_signal"] = "EXTREME_OVERSOLD"
            # Standard oversold (RSI < 30) = Buy signal
            elif rsi_val < config.RSI_OS:
                bullish_points += 2  # Double weight for oversold
                rsi_trigger = True
                details["rsi_signal"] = "OVERSOLD"
            # Extreme overbought (RSI > 75) = Strong sell signal
            elif rsi_val > 75:
                bearish_points += 3
                details["rsi_signal"] = "EXTREME_OVERBOUGHT"
            # Standard overbought (RSI > 70) = Sell signal
            elif rsi_val > config.RSI_OB:
                bearish_points += 2
                details["rsi_signal"] = "OVERBOUGHT"
            else:
                details["rsi_signal"] = "NEUTRAL"
    
    # 10. MACD
    if state.klines:
        macd_line, signal_line, histogram = indicators.macd(state.klines)
        if macd_line is not None and signal_line is not None:
            details["macd"] = macd_line
            details["macd_signal"] = signal_line
            details["macd_hist"] = histogram
            total_indicators += 1
            if macd_line > signal_line:
                bullish_points += 1
            elif macd_line < signal_line:
                bearish_points += 1
    
    # 11. VWAP
    if state.klines:
        vwap_val = indicators.vwap(state.klines)
        if vwap_val > 0:
            details["vwap"] = vwap_val
            total_indicators += 1
            if state.mid > vwap_val:
                bullish_points += 1
            elif state.mid < vwap_val:
                bearish_points += 1
    
    # 12. EMA Crossover
    if state.klines:
        ema_s, ema_l = indicators.emas(state.klines)
        if ema_s is not None and ema_l is not None:
            details["ema_short"] = ema_s
            details["ema_long"] = ema_l
            total_indicators += 1
            if ema_s > ema_l:
                bullish_points += 1
            elif ema_s < ema_l:
                bearish_points += 1
    
    # 13. Heikin Ashi Streak
    if state.klines:
        streak = indicators.ha_streak(state.klines)
        details["ha_streak"] = streak
        total_indicators += 1
        if streak >= 3:
            bullish_points += 1
        elif streak <= -3:
            bearish_points += 1
    
    # ═══════════════════════════════════════════════════════════════════════
    # CALCULATE FINAL SIGNAL
    # ═══════════════════════════════════════════════════════════════════════
    
    details["bullish_points"] = bullish_points
    details["bearish_points"] = bearish_points
    details["total_indicators"] = total_indicators
    
    if total_indicators == 0:
        return Signal(direction="NEUTRAL", confidence=0, details=details)
    
    net_score = bullish_points - bearish_points
    max_possible = total_indicators
    
    # Normalize to 1-10 confidence
    confidence = min(10, max(1, abs(int((net_score / max_possible) * 10))))
    
    if net_score > 0:
        direction = "BULLISH"
    elif net_score < 0:
        direction = "BEARISH"
    else:
        direction = "NEUTRAL"
        confidence = 0
    
    return Signal(direction=direction, confidence=confidence, details=details, rsi_trigger=rsi_trigger)
