"""
Risk management module for Polymarket Trading Bot.
Handles position limits, stop-loss, take-profit, trailing stops, and partial profit taking.
"""
import time
from dataclasses import dataclass, field
from typing import Optional
from . import config


@dataclass
class Position:
    """Represents an open trading position."""
    token_id: str
    side: str  # "UP" or "DOWN"
    entry_price: float
    size_usd: float
    shares: float
    entry_time: float
    order_id: Optional[str] = None
    # Enhanced fields for profit booking
    highest_price: float = 0.0  # Track peak price for trailing stop
    partial_sold: bool = False  # Track if partial profit was taken
    original_shares: float = 0.0  # Original position size before partial sells
    rsi_triggered: bool = False  # True if this was an RSI-based entry (uses tighter profit booking)
    
    def __post_init__(self):
        if self.highest_price == 0.0:
            self.highest_price = self.entry_price
        if self.original_shares == 0.0:
            self.original_shares = self.shares
    
    @property
    def age_seconds(self) -> float:
        return time.time() - self.entry_time
    
    @property
    def pnl_pct(self) -> float:
        """Current P&L percentage based on highest price."""
        if self.entry_price <= 0:
            return 0.0
        return ((self.highest_price - self.entry_price) / self.entry_price) * 100


@dataclass
class RiskManager:
    """Manages trading risk and position tracking with advanced profit booking."""
    positions: list[Position] = field(default_factory=list)
    daily_pnl: float = 0.0
    last_trade_time: dict = field(default_factory=dict)  # market -> timestamp
    trading_enabled: bool = True
    
    @property
    def open_position_count(self) -> int:
        return len(self.positions)
    
    @property
    def can_open_position(self) -> bool:
        """Check if we can open a new position."""
        if not self.trading_enabled:
            return False
        if self.open_position_count >= config.MAX_POSITIONS:
            return False
        return True
    
    def can_trade_market(self, market_id: str) -> bool:
        """Check if cooldown period has passed for a market."""
        last_trade = self.last_trade_time.get(market_id, 0)
        return (time.time() - last_trade) >= config.TRADE_COOLDOWN_SECONDS
    
    def record_trade(self, market_id: str):
        """Record a trade for cooldown tracking."""
        self.last_trade_time[market_id] = time.time()
    
    def add_position(self, position: Position):
        """Add a new open position."""
        self.positions.append(position)
    
    def remove_position(self, token_id: str) -> Optional[Position]:
        """Remove and return a position by token ID."""
        for i, pos in enumerate(self.positions):
            if pos.token_id == token_id:
                return self.positions.pop(i)
        return None
    
    def update_highest_price(self, token_id: str, current_price: float):
        """Update the highest price seen for trailing stop calculation."""
        for pos in self.positions:
            if pos.token_id == token_id:
                if current_price > pos.highest_price:
                    pos.highest_price = current_price
                break
    
    def check_stop_loss(self, position: Position, current_price: float) -> bool:
        """Check if position should be closed due to stop-loss."""
        pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
        return pnl_pct <= -config.STOP_LOSS_PCT
    
    def check_trailing_stop(self, position: Position, current_price: float) -> bool:
        """
        Check if trailing stop should trigger.
        Trailing stop activates after price has risen and then falls back.
        RSI-triggered positions use tighter trailing stop.
        """
        if position.highest_price <= position.entry_price:
            return False
        
        # Use RSI-specific threshold if this was an RSI-triggered trade
        trailing_threshold = config.RSI_TRAILING_STOP_PCT if position.rsi_triggered else config.TRAILING_STOP_PCT
        
        # Calculate how much price has dropped from the highest point
        drop_from_high_pct = ((position.highest_price - current_price) / position.highest_price) * 100
        
        # Only trigger trailing stop if we were in profit and now dropping
        gain_from_entry_pct = ((position.highest_price - position.entry_price) / position.entry_price) * 100
        
        # Activate trailing stop only if we gained at least the trailing threshold
        if gain_from_entry_pct >= trailing_threshold:
            return drop_from_high_pct >= trailing_threshold
        
        return False
    
    def check_partial_profit(self, position: Position, current_price: float) -> bool:
        """Check if we should take partial profit (sell 50%). RSI trades use lower threshold."""
        if position.partial_sold:
            return False
        
        # Use RSI-specific threshold if this was an RSI-triggered trade
        partial_threshold = config.RSI_PARTIAL_PROFIT_PCT if position.rsi_triggered else config.PARTIAL_PROFIT_PCT
        
        pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
        return pnl_pct >= partial_threshold
    
    def check_take_profit(self, position: Position, current_price: float) -> bool:
        """Check if position should be fully closed due to take-profit. RSI trades use lower threshold."""
        # Use RSI-specific threshold if this was an RSI-triggered trade
        take_profit_threshold = config.RSI_FULL_TAKE_PROFIT_PCT if position.rsi_triggered else config.FULL_TAKE_PROFIT_PCT
        
        pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
        return pnl_pct >= take_profit_threshold
    
    def mark_partial_sold(self, token_id: str, shares_sold: float):
        """Mark position as having taken partial profit."""
        for pos in self.positions:
            if pos.token_id == token_id:
                pos.partial_sold = True
                pos.shares -= shares_sold
                pos.size_usd = pos.shares * pos.entry_price
                break
    
    def update_daily_pnl(self, pnl: float):
        """Update daily P&L and check daily loss limit."""
        self.daily_pnl += pnl
        
        # Check daily loss limit (as percentage of starting capital)
        starting_capital = config.POSITION_SIZE_USD * config.MAX_POSITIONS
        loss_pct = (-self.daily_pnl / starting_capital) * 100 if self.daily_pnl < 0 else 0
        
        if loss_pct >= config.DAILY_LOSS_LIMIT_PCT:
            self.trading_enabled = False
            print(f"  [RISK] Daily loss limit reached ({loss_pct:.1f}%), trading disabled")
    
    def reset_daily(self):
        """Reset daily tracking (call at market open)."""
        self.daily_pnl = 0.0
        self.trading_enabled = True
    
    def get_position_for_token(self, token_id: str) -> Optional[Position]:
        """Get position for a specific token."""
        for pos in self.positions:
            if pos.token_id == token_id:
                return pos
        return None
    
    def check_time_based_stop(self, position: Position) -> bool:
        """Check if position should be closed due to age."""
        max_age_seconds = config.MAX_POSITION_AGE_HOURS * 3600
        return position.age_seconds >= max_age_seconds
    
    def check_trend_reversal(self, position: Position, current_price: float, momentum: float = 0) -> bool:
        """
        Check if market is reversing against position - intelligent early exit.
        
        This triggers when:
        - Price was in profit but now declining toward entry
        - Momentum shifted against position direction
        - Position is at risk of going from profit to loss
        """
        pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
        
        # Only check reversal if we were in profit at some point
        if position.highest_price <= position.entry_price:
            return False
        
        peak_gain_pct = ((position.highest_price - position.entry_price) / position.entry_price) * 100
        
        # If we had significant gains (>10%) but now dropping back toward entry (profit < 5%)
        if peak_gain_pct >= 10 and pnl_pct < 5:
            return True
        
        # If momentum is strongly negative and we're losing gains
        if momentum < -0.5 and pnl_pct < peak_gain_pct * 0.5:
            return True
        
        return False
    
    def calculate_dynamic_profit_target(self, position: Position, time_remaining: float = 0) -> float:
        """
        Calculate dynamic profit target between 25-85% based on conditions.
        
        Higher targets when:
        - More time remaining
        - Strong trend
        - RSI triggered entry (higher confidence)
        
        Lower targets when:
        - Less time remaining
        - Volatile conditions
        """
        # Base target
        base_target = config.PARTIAL_PROFIT_PCT  # 25%
        max_target = config.MAX_PROFIT_TARGET_PCT  # 85%
        
        target = base_target
        
        # RSI trades can aim higher
        if position.rsi_triggered:
            target += 10
        
        # Adjust based on time remaining (more time = higher target)
        if time_remaining > 600:  # > 10 min
            target += 10
        elif time_remaining > 300:  # > 5 min
            target += 5
        elif time_remaining < 120:  # < 2 min - take what we can
            target = max(25, target - 20)
        
        # Cap at max
        return min(target, max_target)
    
    def should_skip_market(self, timeframe: str, time_remaining: float) -> bool:
        """
        Check if we should skip trading this market due to timing.
        - 15m: Skip if < 7 min remaining
        - 1h: Skip if < 10 min remaining
        """
        if timeframe == "15m":
            return time_remaining < config.MIN_TIME_15M_SECONDS
        elif timeframe == "1h":
            return time_remaining < config.MIN_TIME_1H_SECONDS
        return False
    
    def check_positions(self, current_prices: dict, momentum: float = 0) -> list[tuple[Position, str, float]]:
        """
        Check all positions for stop-loss, take-profit, trailing stop, or partial profit.
        
        Args:
            current_prices: dict of token_id -> current_price
            momentum: current market momentum (-1 to 1)
            
        Returns:
            List of (position, reason, amount_pct) tuples for positions that need action.
            amount_pct: 1.0 for full exit, 0.5 for partial profit
        """
        actions = []
        
        for position in self.positions:
            if position.token_id not in current_prices:
                continue
            
            current_price = current_prices[position.token_id]
            
            # Update highest price for trailing stop
            self.update_highest_price(position.token_id, current_price)
            
            # Check in priority order
            if self.check_stop_loss(position, current_price):
                actions.append((position, "stop_loss", 1.0))
            elif self.check_take_profit(position, current_price):
                actions.append((position, "take_profit", 1.0))
            elif self.check_trailing_stop(position, current_price):
                actions.append((position, "trailing_stop", 1.0))
            elif self.check_trend_reversal(position, current_price, momentum):
                actions.append((position, "reversal", 1.0))
            elif self.check_time_based_stop(position):
                actions.append((position, "time_stop", 1.0))
            elif self.check_partial_profit(position, current_price):
                actions.append((position, "partial_profit", 0.5))
        
        return actions
    
    def calculate_pnl(self, position: Position, exit_price: float, shares: float = None) -> float:
        """Calculate P&L for a position or partial position."""
        shares = shares or position.shares
        return (exit_price - position.entry_price) * shares
    
    def calculate_position_size(self, confidence: int) -> float:
        """Calculate position size based on signal confidence."""
        if confidence <= 0:
            return config.MIN_POSITION_SIZE_USD
        
        # Linear scaling from MIN to MAX based on confidence (1-10)
        range_usd = config.MAX_POSITION_SIZE_USD - config.MIN_POSITION_SIZE_USD
        scaled = config.MIN_POSITION_SIZE_USD + (range_usd * (confidence / 10))
        
        return min(config.MAX_POSITION_SIZE_USD, max(config.MIN_POSITION_SIZE_USD, scaled))


def validate_trade(risk: RiskManager, market_id: str, action: str) -> tuple[bool, str]:
    """
    Validate if a trade can be executed.
    
    Returns:
        (can_trade, reason)
    """
    if not risk.trading_enabled:
        return False, "Trading disabled due to daily loss limit"
    
    if not risk.can_open_position:
        return False, f"Max positions ({config.MAX_POSITIONS}) reached"
    
    if not risk.can_trade_market(market_id):
        remaining = config.TRADE_COOLDOWN_SECONDS - (time.time() - risk.last_trade_time.get(market_id, 0))
        return False, f"Market cooldown: {remaining:.0f}s remaining"
    
    return True, "OK"
