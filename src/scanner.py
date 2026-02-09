"""
Multi-Coin Market Scanner for Polymarket Trading Bot.
Scans BTC, ETH, SOL across 15m and 1h timeframes to find best opportunities.
"""
import asyncio
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from . import config
from . import feeds
from . import indicators
from .signals import Signal, calculate_signal


@dataclass
class MarketOpportunity:
    """Represents a trading opportunity in a specific market."""
    coin: str
    timeframe: str
    score: float
    signal: Signal
    reason: str
    time_remaining: float  # seconds until expiry
    pm_up_id: Optional[str] = None
    pm_dn_id: Optional[str] = None
    
    @property
    def is_tradeable(self) -> bool:
        """Check if opportunity meets timing requirements."""
        if self.timeframe == "15m":
            return self.time_remaining >= config.MIN_TIME_15M_SECONDS
        elif self.timeframe == "1h":
            return self.time_remaining >= config.MIN_TIME_1H_SECONDS
        return True


class MarketScanner:
    """Scans multiple markets to find best trading opportunities."""
    
    COINS = ["BTC", "ETH", "SOL"]
    TIMEFRAMES = ["15m", "1h"]
    
    def __init__(self):
        self.states: dict[str, feeds.State] = {}  # "BTC_15m" -> State
        self.last_scan: float = 0
        self.scan_interval = 30  # seconds
    
    async def initialize(self) -> None:
        """Initialize state objects for all markets."""
        for coin in self.COINS:
            for tf in self.TIMEFRAMES:
                key = f"{coin}_{tf}"
                self.states[key] = feeds.State()
    
    async def scan_market(self, coin: str, tf: str) -> Optional[MarketOpportunity]:
        """Scan a single market and return opportunity if found."""
        key = f"{coin}_{tf}"
        state = self.states.get(key)
        
        if not state:
            state = feeds.State()
            self.states[key] = state
        
        try:
            # Fetch Polymarket tokens
            pm_up, pm_dn = feeds.fetch_pm_tokens(coin, tf, state)
            state.pm_up_id = pm_up
            state.pm_dn_id = pm_dn
            
            if not pm_up:
                # No Polymarket market available for this coin/tf
                return None
            
            # Bootstrap Binance data
            binance_sym = config.COIN_BINANCE.get(coin)
            kline_iv = config.TF_KLINE.get(tf)
            
            if not binance_sym or not kline_iv:
                return None
            
            await feeds.bootstrap(binance_sym, kline_iv, state)
            
            # Calculate signal
            signal = calculate_signal(state)
            
            # Calculate time remaining (default to 10 min if not available)
            time_remaining = 600.0  # Default 10 min
            if state.market_expiry_ts and state.market_expiry_ts > 0:
                time_remaining = max(0, state.market_expiry_ts - time.time())
            
            # Calculate opportunity score
            score = self._calculate_score(signal, time_remaining, tf, state)
            
            # Build reason string
            reason = self._build_reason(signal, state)
            
            return MarketOpportunity(
                coin=coin,
                timeframe=tf,
                score=score,
                signal=signal,
                reason=reason,
                time_remaining=time_remaining,
                pm_up_id=pm_up,
                pm_dn_id=pm_dn
            )
            
        except Exception as e:
            # Silently continue on error
            return None
    
    def _calculate_score(self, signal: Signal, time_remaining: float, tf: str, state: feeds.State) -> float:
        """
        Calculate opportunity score (0-10) based on:
        - Signal strength/confidence
        - Time remaining
        - RSI trigger (bonus)
        - Trend alignment
        """
        score = 0.0
        
        # Base score from signal confidence (0-10)
        if signal.direction != "NEUTRAL":
            score = signal.confidence
        
        # RSI trigger bonus (+2)
        if signal.rsi_trigger:
            score += 2
        
        # Time bonus (more time = better)
        if tf == "15m":
            if time_remaining >= 600:  # 10+ min
                score += 1
            elif time_remaining < config.MIN_TIME_15M_SECONDS:
                score -= 5  # Heavy penalty for low time
        elif tf == "1h":
            if time_remaining >= 1800:  # 30+ min
                score += 1
            elif time_remaining < config.MIN_TIME_1H_SECONDS:
                score -= 5
        
        # Trend alignment bonus - check if multiple indicators agree
        details = signal.details
        if details.get("bullish_points", 0) >= 5 or details.get("bearish_points", 0) >= 5:
            score += 1
        
        return max(0, min(10, score))
    
    def _build_reason(self, signal: Signal, state: feeds.State) -> str:
        """Build human-readable reason for opportunity."""
        reasons = []
        details = signal.details
        
        # RSI
        rsi_signal = details.get("rsi_signal", "")
        if rsi_signal in ["OVERSOLD", "EXTREME_OVERSOLD"]:
            rsi_val = details.get("rsi", 0)
            reasons.append(f"RSI={rsi_val:.0f}")
        elif rsi_signal in ["OVERBOUGHT", "EXTREME_OVERBOUGHT"]:
            rsi_val = details.get("rsi", 0)
            reasons.append(f"RSI={rsi_val:.0f}")
        
        # MACD
        if details.get("macd") is not None:
            macd = details.get("macd", 0)
            macd_sig = details.get("macd_signal", 0)
            if macd > macd_sig:
                reasons.append("MACD+")
            else:
                reasons.append("MACD-")
        
        # Order book
        obi = details.get("obi", 0)
        if abs(obi) > 0.1:
            reasons.append(f"OBI={obi:+.0%}")
        
        return " | ".join(reasons) if reasons else signal.direction
    
    async def scan_all(self) -> List[MarketOpportunity]:
        """Scan all markets and return sorted opportunities."""
        opportunities = []
        all_scanned = []
        
        for coin in self.COINS:
            for tf in self.TIMEFRAMES:
                opp = await self.scan_market(coin, tf)
                if opp:
                    all_scanned.append(opp)
                    # Include if: has signal direction AND (has time OR is tradeable)
                    if opp.signal.direction != "NEUTRAL" and opp.score >= 3:
                        opportunities.append(opp)
        
        # If no good opportunities, include best available anyway
        if not opportunities and all_scanned:
            # Just take the best scored one regardless of threshold
            all_scanned.sort(key=lambda x: x.score, reverse=True)
            if all_scanned[0].signal.direction != "NEUTRAL":
                opportunities.append(all_scanned[0])
        
        # Sort by score descending
        opportunities.sort(key=lambda x: x.score, reverse=True)
        
        self.last_scan = time.time()
        return opportunities
    
    def select_best(self, opportunities: List[MarketOpportunity]) -> Optional[MarketOpportunity]:
        """Select the best opportunity from the list."""
        if not opportunities:
            return None
        
        # Return highest scoring opportunity
        return opportunities[0]
    
    def format_scan_results(self, opportunities: List[MarketOpportunity]) -> str:
        """Format scan results for compact logging."""
        if not opportunities:
            return "No opportunities"
        
        lines = []
        for opp in opportunities[:3]:  # Top 3
            arrow = "↑" if opp.signal.direction == "BULLISH" else "↓"
            time_min = int(opp.time_remaining / 60)
            lines.append(f"{opp.coin} {opp.timeframe} {arrow} {opp.score:.1f} ({time_min}m) {opp.reason}")
        
        return " | ".join(lines)


# Global scanner instance
_scanner: Optional[MarketScanner] = None


def get_scanner() -> MarketScanner:
    """Get or create the global scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = MarketScanner()
    return _scanner
