"""
Polymarket Smart Auto Trading Bot
Fully autonomous mode - auto-selects coin, timeframe, and manages trades intelligently.
Works on Linux, Windows, Termux, and servers.
"""
import sys
import os
import asyncio
import argparse
import signal
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout

from src import config
from src import feeds
from src.signals import calculate_signal
from src.trader import Trader
from src.scanner import MarketScanner, MarketOpportunity
from src.learner import get_learner, TradeLearner

console = Console(force_terminal=True)

# Global state
_shutdown = False
_trader = None
_learner = None


def log(msg: str, level: str = "INFO"):
    """Compact timestamped logging."""
    ts = datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "📊", "BUY": "💰", "SELL": "✅", "WARN": "⚠️", "ERR": "❌", "SKIP": "⏭️"}
    icon = icons.get(level, "•")
    print(f"[{ts}] {icon} {msg}")


async def auto_trading_loop(trader: Trader, scanner: MarketScanner, learner: TradeLearner):
    """
    Main autonomous trading loop with self-learning.
    Scans all markets, selects best opportunity, trades, learns, and adapts.
    """
    global _shutdown
    
    log("Starting smart auto-trading mode")
    log(f"Settings: ${config.MIN_POSITION_SIZE_USD}-${config.MAX_POSITION_SIZE_USD} | Max {config.MAX_POSITIONS} positions | SL {config.STOP_LOSS_PCT}%")
    log(learner.get_summary())
    
    current_coin = None
    current_tf = None
    state = feeds.State()
    
    while not _shutdown:
        try:
            # ═══════════════════════════════════════════════════════════════
            # STEP 1: Check existing positions first
            # ═══════════════════════════════════════════════════════════════
            if trader.risk.positions:
                for pos in trader.risk.positions:
                    # Get current price
                    price = trader.get_price(pos.token_id)
                    if price:
                        pnl_pct = ((price - pos.entry_price) / pos.entry_price) * 100
                        age_min = int(pos.age_seconds / 60)
                        log(f"Position {pos.side}: {pnl_pct:+.1f}% ({age_min}m)", "INFO")
                
                # Check for exits
                prices = {pos.token_id: trader.get_price(pos.token_id) or pos.entry_price 
                         for pos in trader.risk.positions}
                actions = trader.risk.check_positions(prices)
                
                for position, reason, amount in actions:
                    price = prices.get(position.token_id, position.entry_price)
                    if amount >= 1.0:
                        result = trader.sell_market(position.token_id, reason=reason)
                        if result.success:
                            pnl = (result.filled_price - position.entry_price) * position.shares
                            pnl_pct = ((result.filled_price - position.entry_price) / position.entry_price) * 100
                            log(f"CLOSED {position.side} @ {result.filled_price:.3f} | P&L: ${pnl:+.2f} ({reason})", "SELL")
                            
                            # Learn from this trade
                            learner.record_trade_outcome(
                                coin="BTC",  # TODO: Store coin in position
                                timeframe="15m",
                                signal_direction="BULLISH" if position.side == "UP" else "BEARISH",
                                rsi_triggered=position.rsi_triggered,
                                rsi_value=50,  # Default if not stored
                                entry_price=position.entry_price,
                                exit_price=result.filled_price,
                                pnl=pnl,
                                pnl_pct=pnl_pct,
                                exit_reason=reason
                            )
                    else:
                        result = trader.sell_partial(position.token_id, percentage=0.5)
                        if result.success:
                            log(f"Partial sell {position.side} @ {result.filled_price:.3f}", "SELL")
            
            # ═══════════════════════════════════════════════════════════════
            # STEP 2: Scan for new opportunities (if we can take more positions)
            # ═══════════════════════════════════════════════════════════════
            if trader.risk.can_open_position:
                log("Scanning BTC|ETH|SOL 15m|1h...")
                
                opportunities = await scanner.scan_all()
                
                if opportunities:
                    best = scanner.select_best(opportunities)
                    log(scanner.format_scan_results(opportunities), "INFO")
                    
                    if best and best.score >= 3:  # Lowered threshold from 6 to 3
                        # Check if learner recommends this pattern
                        rsi_val = best.signal.details.get("rsi", 50)
                        should_trade, skip_reason = learner.should_trade_pattern(
                            best.coin, best.timeframe, best.signal.direction, rsi_val
                        )
                        
                        if not should_trade:
                            log(f"Skip {best.coin} {best.timeframe} - {skip_reason}", "SKIP")
                        elif trader.risk.should_skip_market(best.timeframe, best.time_remaining):
                            time_min = int(best.time_remaining / 60)
                            log(f"Skip {best.coin} {best.timeframe} - only {time_min}m left", "SKIP")
                        else:
                            # Get confidence boost from learner
                            confidence_boost = learner.get_confidence_boost(
                                best.coin, best.timeframe, best.signal.direction, rsi_val
                            )
                            adjusted_score = best.score + confidence_boost
                            
                            # Execute trade
                            token_id = best.pm_up_id if best.signal.direction == "BULLISH" else best.pm_dn_id
                            side = "UP" if best.signal.direction == "BULLISH" else "DOWN"
                            
                            # Calculate position size ($1-5 based on confidence)
                            base_size = config.MIN_POSITION_SIZE_USD + (
                                (config.MAX_POSITION_SIZE_USD - config.MIN_POSITION_SIZE_USD) * 
                                (adjusted_score / 10)
                            )
                            # Adjust size based on learning
                            size = learner.get_adjusted_position_size(base_size)
                            size = round(min(size, config.MAX_POSITION_SIZE_USD), 2)
                            
                            result = trader.buy_market(
                                token_id=token_id,
                                amount_usd=size,
                                side=side,
                                confidence=best.signal.confidence,
                                signal_direction=best.signal.direction,
                                rsi_triggered=best.signal.rsi_trigger
                            )
                            
                            if result.success:
                                rsi_tag = " [RSI]" if best.signal.rsi_trigger else ""
                                log(f"BUY ${size:.2f} {best.coin} {best.timeframe} {side} @ {result.filled_price:.3f}{rsi_tag} | {best.reason}", "BUY")
                            else:
                                log(f"Trade failed: {result.error}", "ERR")
                    else:
                        log("No strong opportunities (score < 6)", "SKIP")
                else:
                    log("No tradeable markets found", "SKIP")
            else:
                open_count = trader.risk.open_position_count
                log(f"Max positions ({open_count}/{config.MAX_POSITIONS}) - waiting", "INFO")
            
            # ═══════════════════════════════════════════════════════════════
            # STEP 3: Wait before next scan
            # ═══════════════════════════════════════════════════════════════
            await asyncio.sleep(15)  # Scan every 15 seconds
            
        except Exception as e:
            log(f"Error: {e}", "ERR")
            await asyncio.sleep(5)
    
    log("Shutting down...", "WARN")


def graceful_shutdown(signum, frame):
    """Handle graceful shutdown."""
    global _shutdown, _trader, _learner
    _shutdown = True
    
    if _trader:
        _trader.save_all_positions()
        stats = _trader.get_daily_stats()
        print(f"\n📊 Final: {stats.get('total_trades', 0)} trades | P&L: ${stats.get('total_pnl', 0):+.2f}")
    
    if _learner:
        print(f"🧠 {_learner.get_summary()}")
    
    print("✓ Shutdown complete")
    sys.exit(0)


async def main():
    """Main entry point for auto trading with self-learning."""
    global _trader, _learner
    
    parser = argparse.ArgumentParser(description="Polymarket Smart Auto Trading Bot")
    parser.add_argument("--paper", action="store_true", help="Paper trading mode")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (signals only)")
    args = parser.parse_args()
    
    print("\n" + "═" * 50)
    print("  🤖 POLYMARKET SMART AUTO TRADING BOT")
    print("  🧠 Self-Learning Mode")
    print("═" * 50)
    
    if args.dry_run:
        print("  Mode: DRY RUN (no trades)")
    elif args.paper:
        print("  Mode: PAPER TRADING")
    else:
        print("  Mode: LIVE TRADING")
    
    print(f"  Position: ${config.MIN_POSITION_SIZE_USD}-${config.MAX_POSITION_SIZE_USD}")
    print(f"  Max Positions: {config.MAX_POSITIONS}")
    print(f"  Stop Loss: {config.STOP_LOSS_PCT}%")
    print(f"  Profit: {config.PARTIAL_PROFIT_PCT}-{config.MAX_PROFIT_TARGET_PCT}%")
    print("═" * 50 + "\n")
    
    # Initialize trader
    trader = Trader(dry_run=args.dry_run, paper=args.paper)
    _trader = trader
    
    if not trader.initialize():
        print("❌ Failed to initialize trader")
        if not (args.dry_run or args.paper):
            return
    
    # Load saved positions
    loaded = trader.load_positions_from_db()
    if loaded > 0:
        print(f"✓ Recovered {loaded} positions")
    
    # Initialize self-learning engine
    learner = get_learner(trader.db)
    _learner = learner
    print(f"✓ Learning engine: {learner.get_summary()}")
    
    # Initialize scanner
    scanner = MarketScanner()
    await scanner.initialize()
    
    print("✓ Ready - Press Ctrl+C to stop\n")
    
    # Run trading loop with learning
    await auto_trading_loop(trader, scanner, learner)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        graceful_shutdown(None, None)
