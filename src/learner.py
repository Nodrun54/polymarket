"""
Self-Learning Trading Module for Polymarket Bot.
Learns from trade outcomes and adapts parameters automatically.
"""
import time
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from . import config


@dataclass
class TradePattern:
    """Represents a trading pattern for learning."""
    coin: str
    timeframe: str
    signal_direction: str
    rsi_triggered: bool
    rsi_range: str  # "oversold", "neutral", "overbought"
    macd_positive: bool
    
    def to_key(self) -> str:
        """Generate unique key for this pattern."""
        return f"{self.coin}_{self.timeframe}_{self.signal_direction}_{self.rsi_range}"


@dataclass
class PatternStats:
    """Statistics for a trading pattern."""
    pattern_key: str
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    avg_profit_pct: float = 0.0
    avg_loss_pct: float = 0.0
    best_trade_pct: float = 0.0
    worst_trade_pct: float = 0.0
    last_updated: float = field(default_factory=time.time)
    
    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.5  # Default 50%
        return self.wins / self.total_trades
    
    @property
    def is_profitable(self) -> bool:
        return self.total_pnl > 0
    
    @property
    def confidence_adjustment(self) -> float:
        """Return confidence boost/reduction based on performance."""
        if self.total_trades < 5:
            return 0  # Not enough data
        
        if self.win_rate >= 0.7:
            return 2  # Strong pattern, boost confidence
        elif self.win_rate >= 0.6:
            return 1  # Good pattern
        elif self.win_rate <= 0.3:
            return -3  # Avoid this pattern
        elif self.win_rate <= 0.4:
            return -1  # Weak pattern
        return 0


class TradeLearner:
    """
    Self-learning engine that adapts trading parameters based on outcomes.
    """
    
    MIN_TRADES_FOR_LEARNING = 5  # Minimum trades before adjusting
    
    def __init__(self, db=None):
        self.db = db
        self.patterns: Dict[str, PatternStats] = {}
        self.recent_trades: List[dict] = []
        self.overall_stats = {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "total_pnl": 0.0,
            "best_coin": None,
            "best_timeframe": None,
            "avoid_patterns": []
        }
        self.load_learned_data()
    
    def load_learned_data(self):
        """Load previously learned patterns from database."""
        if self.db:
            try:
                saved = self.db.get_learned_patterns()
                if saved:
                    for key, data in saved.items():
                        self.patterns[key] = PatternStats(**data)
            except Exception:
                pass  # Start fresh if no data
    
    def save_learned_data(self):
        """Save learned patterns to database."""
        if self.db:
            try:
                data = {k: asdict(v) for k, v in self.patterns.items()}
                self.db.save_learned_patterns(data)
            except Exception:
                pass
    
    def record_trade_outcome(
        self,
        coin: str,
        timeframe: str,
        signal_direction: str,
        rsi_triggered: bool,
        rsi_value: float,
        entry_price: float,
        exit_price: float,
        pnl: float,
        pnl_pct: float,
        exit_reason: str
    ):
        """
        Record a completed trade and learn from it.
        """
        # Determine RSI range
        if rsi_value < 30:
            rsi_range = "oversold"
        elif rsi_value > 70:
            rsi_range = "overbought"
        else:
            rsi_range = "neutral"
        
        # Create pattern
        pattern = TradePattern(
            coin=coin,
            timeframe=timeframe,
            signal_direction=signal_direction,
            rsi_triggered=rsi_triggered,
            rsi_range=rsi_range,
            macd_positive=signal_direction == "BULLISH"
        )
        pattern_key = pattern.to_key()
        
        # Get or create stats
        if pattern_key not in self.patterns:
            self.patterns[pattern_key] = PatternStats(pattern_key=pattern_key)
        
        stats = self.patterns[pattern_key]
        
        # Update stats
        stats.total_trades += 1
        stats.total_pnl += pnl
        stats.last_updated = time.time()
        
        is_win = pnl > 0
        if is_win:
            stats.wins += 1
            if pnl_pct > stats.best_trade_pct:
                stats.best_trade_pct = pnl_pct
            # Update avg profit
            if stats.wins > 0:
                stats.avg_profit_pct = (stats.avg_profit_pct * (stats.wins - 1) + pnl_pct) / stats.wins
        else:
            stats.losses += 1
            if pnl_pct < stats.worst_trade_pct:
                stats.worst_trade_pct = pnl_pct
            # Update avg loss
            if stats.losses > 0:
                stats.avg_loss_pct = (stats.avg_loss_pct * (stats.losses - 1) + pnl_pct) / stats.losses
        
        # Update overall stats
        self.overall_stats["total_trades"] += 1
        self.overall_stats["total_pnl"] += pnl
        if is_win:
            self.overall_stats["wins"] += 1
        else:
            self.overall_stats["losses"] += 1
        
        # Check if pattern should be avoided
        if stats.total_trades >= self.MIN_TRADES_FOR_LEARNING and stats.win_rate <= 0.3:
            if pattern_key not in self.overall_stats["avoid_patterns"]:
                self.overall_stats["avoid_patterns"].append(pattern_key)
                print(f"  [Learn] Avoiding pattern: {pattern_key} (win rate: {stats.win_rate:.0%})")
        
        # Log learning
        print(f"  [Learn] {pattern_key}: {stats.wins}W/{stats.losses}L ({stats.win_rate:.0%}) | P&L: ${stats.total_pnl:+.2f}")
        
        # Save to database
        self.save_learned_data()
    
    def should_trade_pattern(self, coin: str, timeframe: str, signal_direction: str, rsi_value: float) -> Tuple[bool, str]:
        """
        Check if we should trade this pattern based on learned data.
        Returns (should_trade, reason)
        """
        if rsi_value < 30:
            rsi_range = "oversold"
        elif rsi_value > 70:
            rsi_range = "overbought"
        else:
            rsi_range = "neutral"
        
        pattern_key = f"{coin}_{timeframe}_{signal_direction}_{rsi_range}"
        
        # Check if pattern should be avoided
        if pattern_key in self.overall_stats.get("avoid_patterns", []):
            return False, f"Avoiding low win-rate pattern"
        
        # Check pattern stats
        if pattern_key in self.patterns:
            stats = self.patterns[pattern_key]
            if stats.total_trades >= self.MIN_TRADES_FOR_LEARNING:
                if stats.win_rate <= 0.3:
                    return False, f"Pattern win rate too low ({stats.win_rate:.0%})"
        
        return True, "OK"
    
    def get_confidence_boost(self, coin: str, timeframe: str, signal_direction: str, rsi_value: float) -> int:
        """
        Get confidence adjustment based on learned patterns.
        Returns: -3 to +2
        """
        if rsi_value < 30:
            rsi_range = "oversold"
        elif rsi_value > 70:
            rsi_range = "overbought"
        else:
            rsi_range = "neutral"
        
        pattern_key = f"{coin}_{timeframe}_{signal_direction}_{rsi_range}"
        
        if pattern_key in self.patterns:
            return int(self.patterns[pattern_key].confidence_adjustment)
        
        return 0
    
    def get_adjusted_position_size(self, base_size: float) -> float:
        """
        Adjust position size based on recent performance.
        Reduce size if losing streak, increase if winning.
        """
        if self.overall_stats["total_trades"] < 10:
            return base_size  # Not enough data
        
        win_rate = self.overall_stats["wins"] / self.overall_stats["total_trades"]
        
        # Reduce size if losing
        if win_rate < 0.4:
            return max(config.MIN_POSITION_SIZE_USD, base_size * 0.5)
        
        # Increase size if winning well
        if win_rate > 0.65:
            return min(config.MAX_POSITION_SIZE_USD, base_size * 1.3)
        
        return base_size
    
    def get_adjusted_profit_target(self, base_target: float, coin: str, timeframe: str) -> float:
        """
        Adjust profit target based on what works for this coin/timeframe.
        """
        # Find best performing pattern for this coin/timeframe
        best_avg = base_target
        for key, stats in self.patterns.items():
            if key.startswith(f"{coin}_{timeframe}_") and stats.win_rate > 0.5:
                if stats.avg_profit_pct > best_avg:
                    best_avg = min(stats.avg_profit_pct * 0.8, config.MAX_PROFIT_TARGET_PCT)
        
        return best_avg
    
    def get_best_opportunities(self) -> List[Tuple[str, str, float]]:
        """
        Return best performing coin/timeframe combinations.
        Returns: List of (coin, timeframe, win_rate)
        """
        results = []
        coin_tf_stats = defaultdict(lambda: {"wins": 0, "total": 0})
        
        for key, stats in self.patterns.items():
            parts = key.split("_")
            if len(parts) >= 2:
                coin_tf = f"{parts[0]}_{parts[1]}"
                coin_tf_stats[coin_tf]["wins"] += stats.wins
                coin_tf_stats[coin_tf]["total"] += stats.total_trades
        
        for coin_tf, data in coin_tf_stats.items():
            if data["total"] >= 5:
                win_rate = data["wins"] / data["total"]
                parts = coin_tf.split("_")
                results.append((parts[0], parts[1], win_rate))
        
        results.sort(key=lambda x: x[2], reverse=True)
        return results
    
    def get_summary(self) -> str:
        """Get human-readable learning summary."""
        if self.overall_stats["total_trades"] == 0:
            return "No trades yet - learning in progress"
        
        win_rate = self.overall_stats["wins"] / self.overall_stats["total_trades"]
        
        lines = [
            f"📊 Learning: {self.overall_stats['total_trades']} trades | {win_rate:.0%} win rate | ${self.overall_stats['total_pnl']:+.2f}"
        ]
        
        # Best patterns
        best = self.get_best_opportunities()
        if best:
            top = best[0]
            lines.append(f"🏆 Best: {top[0]} {top[1]} ({top[2]:.0%})")
        
        # Avoided patterns
        avoid_count = len(self.overall_stats.get("avoid_patterns", []))
        if avoid_count > 0:
            lines.append(f"❌ Avoiding {avoid_count} low-performing patterns")
        
        return " | ".join(lines)


# Global learner instance
_learner: Optional[TradeLearner] = None


def get_learner(db=None) -> TradeLearner:
    """Get or create the global learner instance."""
    global _learner
    if _learner is None:
        _learner = TradeLearner(db)
    return _learner
