"""
Polymarket Auto Trading Bot
Main entry point with async orchestration, terminal dashboard, and automated profit booking.
"""
import sys
import os
import asyncio
import argparse
import signal
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text

from src import config
from src import feeds
from src import indicators
from src.signals import calculate_signal, Signal
from src.trader import Trader


console = Console(force_terminal=True)

# Global shutdown flag
_shutdown_event = asyncio.Event()
_trader_instance = None


def pick(title: str, options: list[str]) -> str:
    """Interactive menu picker."""
    console.print(f"\n[bold]{title}[/bold]")
    for i, o in enumerate(options, 1):
        console.print(f"  [{i}] {o}")
    while True:
        raw = input("  → ").strip()
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        console.print("  [red]invalid – try again[/red]")


def render_dashboard(state: feeds.State, coin: str, tf: str, signal: Signal, trader: Trader) -> Panel:
    """Render the trading dashboard."""
    layout = Layout()
    
    # Main table
    table = Table(title=f"🎰 {coin} {tf} Trading Dashboard", expand=True)
    table.add_column("Category", style="cyan", width=15)
    table.add_column("Indicator", style="white", width=20)
    table.add_column("Value", style="yellow", width=15)
    table.add_column("Signal", style="green", width=10)
    
    # Prices
    table.add_row(
        "📊 Prices",
        "Binance Mid",
        f"${state.mid:,.2f}" if state.mid else "---",
        ""
    )
    table.add_row(
        "",
        "PM Up Price",
        f"{state.pm_up:.4f}" if state.pm_up else "---",
        ""
    )
    table.add_row(
        "",
        "PM Down Price",
        f"{state.pm_dn:.4f}" if state.pm_dn else "---",
        ""
    )
    
    # Market Expiry
    if state.market_expiry_ts:
        remaining = state.seconds_to_expiry()
        if remaining:
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            expiry_color = "red" if remaining < 120 else "yellow" if remaining < 300 else "green"
            table.add_row(
                "",
                "Market Expires",
                f"{mins}m {secs}s",
                f"[{expiry_color}]{'⚠️' if remaining < 120 else '⏱️'}[/{expiry_color}]"
            )
    
    # Order Book
    if state.bids and state.asks:
        obi_val = indicators.obi(state.bids, state.asks, state.mid)
        obi_signal = "🟢 BUY" if obi_val > config.OBI_THRESH else "🔴 SELL" if obi_val < -config.OBI_THRESH else "⚪"
        table.add_row("📗 Order Book", "OBI", f"{obi_val:+.3f}", obi_signal)
        
        buy_walls, sell_walls = indicators.walls(state.bids, state.asks)
        table.add_row("", "Buy Walls", str(len(buy_walls)), "")
        table.add_row("", "Sell Walls", str(len(sell_walls)), "")
    
    # Flow
    if state.trades:
        cvd_1m = indicators.cvd(state.trades, 60)
        cvd_signal = "🟢" if cvd_1m > 0 else "🔴" if cvd_1m < 0 else "⚪"
        table.add_row("📈 Flow", "CVD 1m", f"${cvd_1m:,.0f}", cvd_signal)
        
        delta_val = indicators.delta(state.trades)
        delta_signal = "🟢" if delta_val > 0 else "🔴" if delta_val < 0 else "⚪"
        table.add_row("", "Delta 1m", f"${delta_val:,.0f}", delta_signal)
    
    # Technical Analysis
    if state.klines:
        rsi_val = indicators.rsi(state.klines)
        if rsi_val:
            rsi_signal = "🟢 OS" if rsi_val < 30 else "🔴 OB" if rsi_val > 70 else "⚪"
            table.add_row("📉 TA", "RSI", f"{rsi_val:.1f}", rsi_signal)
        
        macd_line, signal_line, hist = indicators.macd(state.klines)
        if macd_line is not None:
            macd_signal = "🟢" if macd_line > signal_line else "🔴"
            table.add_row("", "MACD", f"{macd_line:.2f}", macd_signal)
        
        ema_s, ema_l = indicators.emas(state.klines)
        if ema_s and ema_l:
            ema_signal = "🟢" if ema_s > ema_l else "🔴"
            table.add_row("", "EMA 5/20", f"{ema_s:.2f}/{ema_l:.2f}", ema_signal)
        
        ha_streak = indicators.ha_streak(state.klines)
        ha_color = "🟢" if ha_streak > 0 else "🔴" if ha_streak < 0 else "⚪"
        table.add_row("", "HA Streak", str(ha_streak), ha_color)
    
    # Signal
    signal_color = "green" if signal.direction == "BULLISH" else "red" if signal.direction == "BEARISH" else "yellow"
    table.add_row("", "", "", "")
    table.add_row(
        f"🎯 [bold {signal_color}]SIGNAL[/bold {signal_color}]",
        signal.direction,
        f"Confidence: {signal.confidence}/10",
        signal.action or "HOLD"
    )
    
    # Positions with profit tracking
    table.add_row("", "", "", "")
    pos_count = trader.risk.open_position_count
    table.add_row(
        "💼 Positions",
        f"{pos_count}/{config.MAX_POSITIONS}",
        f"P&L: ${trader.risk.daily_pnl:+.2f}",
        "🟢" if trader.risk.trading_enabled else "🔴 STOPPED"
    )
    
    # Show open positions if any
    for pos in trader.risk.positions:
        current_price = state.pm_up if pos.side == "UP" else state.pm_dn
        if current_price:
            pnl_pct = ((current_price - pos.entry_price) / pos.entry_price) * 100
            pnl_color = "green" if pnl_pct > 0 else "red"
            partial_marker = "½" if pos.partial_sold else ""
            table.add_row(
                f"  └─ {pos.side}{partial_marker}",
                f"Entry: {pos.entry_price:.4f}",
                f"Now: {current_price:.4f}",
                f"[{pnl_color}]{pnl_pct:+.1f}%[/{pnl_color}]"
            )
    
    # Status
    status = []
    if state.binance_connected:
        status.append("[green]Binance ✓[/green]")
    else:
        status.append("[red]Binance ✗[/red]")
    if state.pm_connected:
        status.append("[green]PM ✓[/green]")
    else:
        status.append("[yellow]PM ○[/yellow]")
    
    # Auto trade status
    if config.AUTO_TRADE_ENABLED:
        status.append("[green]AUTO[/green]")
    else:
        status.append("[yellow]MANUAL[/yellow]")
    
    now = datetime.now().strftime("%H:%M:%S")
    footer = f"{' | '.join(status)} | {now}"
    
    return Panel(table, subtitle=footer)


async def trading_loop(state: feeds.State, coin: str, tf: str, trader: Trader):
    """Main trading loop - generates signals, executes trades, manages profit booking."""
    await asyncio.sleep(5)  # Wait for initial data
    
    while True:
        try:
            # Calculate signal from all indicators
            signal = calculate_signal(state)
            
            # Build current prices dict for position management
            current_prices = {}
            if state.pm_up_id and state.pm_up:
                current_prices[state.pm_up_id] = state.pm_up
            if state.pm_dn_id and state.pm_dn:
                current_prices[state.pm_dn_id] = state.pm_dn
            
            # Check for market expiry - exit all positions
            if state.is_near_expiry() and trader.risk.open_position_count > 0:
                console.print(f"[yellow]⚠️ Market expiring soon - closing all positions[/yellow]")
                trader.close_all_positions(reason="market_expiry")
            
            # Check positions for stop-loss / take-profit / trailing stop / partial profit
            if current_prices and trader.risk.positions:
                actions = trader.risk.check_positions(current_prices)
                for position, reason, amount_pct in actions:
                    if amount_pct < 1.0:
                        # Partial profit taking
                        result = trader.sell_partial(position.token_id, amount_pct, reason)
                        if result.success:
                            console.print(f"[green]✓ Partial profit: sold 50% of {position.side}[/green]")
                    else:
                        # Full exit
                        result = trader.sell_market(position.token_id, position.shares, reason)
                        if result.success:
                            reason_emoji = {
                                "stop_loss": "🔴",
                                "take_profit": "🟢",
                                "trailing_stop": "🟡"
                            }.get(reason, "⚪")
                            console.print(f"{reason_emoji} Closed {position.side}: {reason}")
            
            # Check if we should open new trades (only if auto trade enabled)
            if (config.AUTO_TRADE_ENABLED and 
                signal.should_trade and 
                trader.risk.trading_enabled and
                not state.is_near_expiry()):
                
                action = signal.action
                
                if action == "BUY_UP" and state.pm_up_id:
                    result = trader.buy_market(
                        token_id=state.pm_up_id,
                        amount_usd=config.POSITION_SIZE_USD,
                        side="UP",
                        confidence=signal.confidence,
                        signal_direction=signal.direction,
                        rsi_triggered=signal.rsi_trigger
                    )
                    if result.success:
                        rsi_tag = " [RSI]" if signal.rsi_trigger else ""
                        console.print(f"[green]✓ Bought UP at {result.filled_price:.4f} (conf: {signal.confidence}){rsi_tag}[/green]")
                
                elif action == "BUY_DOWN" and state.pm_dn_id:
                    result = trader.buy_market(
                        token_id=state.pm_dn_id,
                        amount_usd=config.POSITION_SIZE_USD,
                        side="DOWN",
                        confidence=signal.confidence,
                        signal_direction=signal.direction,
                        rsi_triggered=signal.rsi_trigger
                    )
                    if result.success:
                        rsi_tag = " [RSI]" if signal.rsi_trigger else ""
                        console.print(f"[red]✓ Bought DOWN at {result.filled_price:.4f} (conf: {signal.confidence}){rsi_tag}[/red]")
            
        except Exception as e:
            console.print(f"[red]Trading loop error: {e}[/red]")
        
        await asyncio.sleep(config.REFRESH)


async def display_loop(state: feeds.State, coin: str, tf: str, trader: Trader):
    """Dashboard display loop."""
    await asyncio.sleep(3)  # Wait for initial data
    
    with Live(console=console, refresh_per_second=1, transient=False) as live:
        while True:
            try:
                if state.mid > 0 or state.klines:
                    signal = calculate_signal(state)
                    live.update(render_dashboard(state, coin, tf, signal, trader))
            except Exception as e:
                console.print(f"[red]Display error: {e}[/red]")
            await asyncio.sleep(config.REFRESH)


async def main():
    """Main entry point."""
    global _trader_instance
    
    parser = argparse.ArgumentParser(description="Polymarket Auto Trading Bot")
    parser.add_argument("--dry-run", action="store_true", help="Show signals without trading")
    parser.add_argument("--paper", action="store_true", help="Paper trading (simulated orders)")
    parser.add_argument("--coin", type=str, choices=config.COINS, help="Coin to trade")
    parser.add_argument("--tf", type=str, choices=config.TIMEFRAMES, help="Timeframe")
    args = parser.parse_args()
    
    console.print("\n[bold magenta]═══════════════════════════════════════════════════════[/bold magenta]")
    console.print("[bold magenta]       POLYMARKET AUTO TRADING BOT v2.0                 [/bold magenta]")
    console.print("[bold magenta]═══════════════════════════════════════════════════════[/bold magenta]\n")
    
    if args.dry_run:
        console.print("[yellow]🔒 DRY RUN MODE - No orders will be placed[/yellow]\n")
    elif args.paper:
        console.print("[blue]📝 PAPER TRADING MODE - Orders are simulated[/blue]\n")
    else:
        console.print("[green]💰 LIVE TRADING MODE - Real orders will be placed![/green]\n")
    
    # Show profit booking settings
    console.print("[bold]Profit Booking Settings:[/bold]")
    console.print(f"  • Stop Loss: -{config.STOP_LOSS_PCT}%")
    console.print(f"  • Partial Profit: +{config.PARTIAL_PROFIT_PCT}% (sell 50%)")
    console.print(f"  • Trailing Stop: {config.TRAILING_STOP_PCT}% drop from peak")
    console.print(f"  • Full Take Profit: +{config.FULL_TAKE_PROFIT_PCT}%")
    console.print(f"  • Time-Based Stop: {config.MAX_POSITION_AGE_HOURS} hours max")
    console.print(f"  • Position Size: ${config.MIN_POSITION_SIZE_USD}-${config.MAX_POSITION_SIZE_USD} (dynamic)")
    console.print(f"  • Exit Before Expiry: {config.EXIT_BEFORE_EXPIRY_SECONDS}s\n")
    
    # Select coin and timeframe
    coin = args.coin or pick("Select coin:", config.COINS)
    tf = args.tf or pick("Select timeframe:", config.TIMEFRAMES)
    
    console.print(f"\n[bold green]Starting {coin} {tf} …[/bold green]\n")
    
    # Initialize trader
    trader = Trader(dry_run=args.dry_run, paper=args.paper)
    _trader_instance = trader
    
    if not trader.initialize():
        console.print("[red]Failed to initialize trader. Check your credentials in .env[/red]")
        if not (args.dry_run or args.paper):
            return
    
    # Load saved positions from database
    loaded_count = trader.load_positions_from_db()
    if loaded_count > 0:
        console.print(f"[green]  ✓ Recovered {loaded_count} positions from database[/green]")
    
    # Initialize state
    state = feeds.State()
    
    # Fetch Polymarket tokens with expiry tracking
    state.pm_up_id, state.pm_dn_id = feeds.fetch_pm_tokens(coin, tf, state)
    if state.pm_up_id:
        console.print(f"  [PM] Up   → {state.pm_up_id[:24]}…")
        console.print(f"  [PM] Down → {state.pm_dn_id[:24]}…")
    else:
        console.print("  [yellow][PM] No market for this coin/timeframe – prices won't show[/yellow]")
    
    # Bootstrap Binance data
    binance_sym = config.COIN_BINANCE[coin]
    kline_iv = config.TF_KLINE[tf]
    console.print("  [Binance] Bootstrapping candles …")
    await feeds.bootstrap(binance_sym, kline_iv, state)
    
    # Show daily stats
    stats = trader.get_daily_stats()
    if stats.get('total_trades', 0) > 0:
        console.print(f"\n[bold]Today's Stats:[/bold] {stats['wins']}W/{stats['losses']}L | P&L: ${stats['total_pnl']:+.2f}")
    
    console.print("\n[bold]Starting data feeds and auto-trading loop...[/bold]")
    console.print("[dim]Press Ctrl+C to stop gracefully[/dim]\n")
    
    # Run all async tasks including market token refresh for 15m markets
    tasks = [
        feeds.ob_poller(binance_sym, state),
        feeds.binance_feed(binance_sym, kline_iv, state),
        feeds.pm_feed(state),
        trading_loop(state, coin, tf, trader),
        display_loop(state, coin, tf, trader),
    ]
    
    # Add market refresh task for short-term markets
    if tf in ["15m", "1h"]:
        tasks.append(feeds.refresh_market_tokens(coin, tf, state))
    
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass


def graceful_shutdown(signum, frame):
    """Handle graceful shutdown on Ctrl+C."""
    global _trader_instance
    console.print("\n[yellow]⚠️ Shutdown signal received...[/yellow]")
    
    if _trader_instance:
        # Save positions to database
        _trader_instance.save_all_positions()
        
        # Show final stats
        stats = _trader_instance.get_daily_stats()
        console.print(f"\n[bold]Final Stats:[/bold]")
        console.print(f"  Trades: {stats.get('total_trades', 0)}")
        console.print(f"  Win/Loss: {stats.get('wins', 0)}/{stats.get('losses', 0)}")
        console.print(f"  P&L: ${stats.get('total_pnl', 0):+.2f}")
    
    console.print("[green]✓ Shutdown complete[/green]")
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        graceful_shutdown(None, None)

