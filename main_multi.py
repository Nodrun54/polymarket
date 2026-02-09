"""
Polymarket Multi-Timeframe Auto Trading Bot
Trades both 15-minute and 1-hour timeframes simultaneously.
"""
import sys
import os
import asyncio
import argparse
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

from src import config
from src import feeds
from src import indicators
from src.signals import calculate_signal, Signal
from src.trader import Trader


console = Console(force_terminal=True)


@dataclass
class MarketState:
    """State for a single market (coin + timeframe)."""
    coin: str
    timeframe: str
    state: feeds.State = field(default_factory=feeds.State)
    signal: Optional[Signal] = None
    last_trade_time: float = 0


class MultiTimeframeBot:
    """Bot that trades multiple timeframes simultaneously."""
    
    def __init__(self, coins: list[str], timeframes: list[str], dry_run: bool = False, paper: bool = False):
        self.coins = coins
        self.timeframes = timeframes
        self.dry_run = dry_run
        self.paper = paper
        self.trader = Trader(dry_run=dry_run, paper=paper)
        self.markets: dict[str, MarketState] = {}
        
        # Create market states for each coin/timeframe combo
        for coin in coins:
            for tf in timeframes:
                key = f"{coin}_{tf}"
                self.markets[key] = MarketState(coin=coin, timeframe=tf)
    
    async def initialize(self) -> bool:
        """Initialize trader and fetch all market tokens."""
        if not self.trader.initialize():
            if not (self.dry_run or self.paper):
                return False
        
        # Fetch Polymarket tokens for each market
        for key, market in self.markets.items():
            market.state.pm_up_id, market.state.pm_dn_id = feeds.fetch_pm_tokens(
                market.coin, market.timeframe
            )
            if market.state.pm_up_id:
                console.print(f"  [PM] {key}: Up → {market.state.pm_up_id[:20]}...")
            else:
                console.print(f"  [yellow][PM] {key}: No active market[/yellow]")
        
        return True
    
    async def run_binance_feeds(self):
        """Run Binance data feeds for all coins."""
        tasks = []
        
        for coin in self.coins:
            binance_sym = config.COIN_BINANCE[coin]
            
            # Use the first timeframe's state for shared Binance data
            # All timeframes for the same coin share the same Binance feed
            primary_key = f"{coin}_{self.timeframes[0]}"
            state = self.markets[primary_key].state
            
            # Bootstrap candles
            kline_iv = config.TF_KLINE[self.timeframes[0]]
            await feeds.bootstrap(binance_sym, kline_iv, state)
            
            # Copy state reference to other timeframes
            for tf in self.timeframes[1:]:
                key = f"{coin}_{tf}"
                self.markets[key].state = state
            
            # Start feeds
            tasks.append(feeds.ob_poller(binance_sym, state))
            tasks.append(feeds.binance_feed(binance_sym, kline_iv, state))
        
        await asyncio.gather(*tasks)
    
    async def run_pm_feeds(self):
        """Run Polymarket feeds for all markets."""
        tasks = []
        for key, market in self.markets.items():
            if market.state.pm_up_id:
                tasks.append(feeds.pm_feed(market.state))
        
        if tasks:
            await asyncio.gather(*tasks)
    
    async def trading_loop(self):
        """Main trading loop for all markets."""
        await asyncio.sleep(5)  # Wait for initial data
        
        while True:
            try:
                for key, market in self.markets.items():
                    # Calculate signal
                    market.signal = calculate_signal(market.state)
                    
                    # Check if we should trade
                    if market.signal.should_trade and self.trader.risk.trading_enabled:
                        action = market.signal.action
                        
                        if action == "BUY_UP" and market.state.pm_up_id:
                            result = self.trader.buy_market(
                                token_id=market.state.pm_up_id,
                                amount_usd=config.POSITION_SIZE_USD,
                                side="UP"
                            )
                            if result.success:
                                console.print(f"[green]✓ {key}: Bought UP at {result.filled_price:.4f}[/green]")
                        
                        elif action == "BUY_DOWN" and market.state.pm_dn_id:
                            result = self.trader.buy_market(
                                token_id=market.state.pm_dn_id,
                                amount_usd=config.POSITION_SIZE_USD,
                                side="DOWN"
                            )
                            if result.success:
                                console.print(f"[red]✓ {key}: Bought DOWN at {result.filled_price:.4f}[/red]")
                    
                    # Check positions for stop-loss / take-profit
                    current_prices = {}
                    if market.state.pm_up_id and market.state.pm_up:
                        current_prices[market.state.pm_up_id] = market.state.pm_up
                    if market.state.pm_dn_id and market.state.pm_dn:
                        current_prices[market.state.pm_dn_id] = market.state.pm_dn
                    
                    positions_to_close = self.trader.risk.check_positions(current_prices)
                    for position, reason in positions_to_close:
                        self.trader.sell_market(position.token_id, position.shares, reason)
                
            except Exception as e:
                console.print(f"[red]Trading error: {e}[/red]")
            
            await asyncio.sleep(config.REFRESH)
    
    def render_market_panel(self, market: MarketState) -> Table:
        """Render a single market's status."""
        table = Table(title=f"📊 {market.coin} {market.timeframe}", expand=True, show_header=False)
        table.add_column("Label", style="cyan", width=12)
        table.add_column("Value", style="yellow", width=15)
        
        state = market.state
        signal = market.signal or Signal(direction="NEUTRAL", confidence=0, details={})
        
        # Prices
        table.add_row("Binance", f"${state.mid:,.2f}" if state.mid else "---")
        table.add_row("PM Up", f"{state.pm_up:.4f}" if state.pm_up else "---")
        table.add_row("PM Down", f"{state.pm_dn:.4f}" if state.pm_dn else "---")
        
        # Key indicators
        if state.klines:
            rsi_val = indicators.rsi(state.klines)
            if rsi_val:
                rsi_color = "green" if rsi_val < 30 else "red" if rsi_val > 70 else "white"
                table.add_row("RSI", f"[{rsi_color}]{rsi_val:.1f}[/{rsi_color}]")
            
            ha_streak = indicators.ha_streak(state.klines)
            ha_color = "green" if ha_streak > 0 else "red" if ha_streak < 0 else "white"
            table.add_row("HA Streak", f"[{ha_color}]{ha_streak}[/{ha_color}]")
        
        # Signal
        sig_color = "green" if signal.direction == "BULLISH" else "red" if signal.direction == "BEARISH" else "yellow"
        table.add_row("Signal", f"[bold {sig_color}]{signal.direction}[/bold {sig_color}]")
        table.add_row("Confidence", f"{signal.confidence}/10")
        table.add_row("Action", signal.action or "HOLD")
        
        return table
    
    def render_dashboard(self) -> Panel:
        """Render the full multi-market dashboard."""
        panels = []
        
        for key, market in self.markets.items():
            panels.append(self.render_market_panel(market))
        
        # Status bar
        now = datetime.now().strftime("%H:%M:%S")
        positions = f"Positions: {self.trader.risk.open_position_count}/{config.MAX_POSITIONS}"
        pnl = f"P&L: ${self.trader.risk.daily_pnl:+.2f}"
        status = "🟢 TRADING" if self.trader.risk.trading_enabled else "🔴 STOPPED"
        
        mode = "DRY RUN" if self.dry_run else "PAPER" if self.paper else "LIVE"
        
        footer = f"{mode} | {positions} | {pnl} | {status} | {now}"
        
        return Panel(
            Columns(panels, equal=True),
            title="🎰 POLYMARKET MULTI-TIMEFRAME BOT",
            subtitle=footer
        )
    
    async def display_loop(self):
        """Dashboard display loop."""
        await asyncio.sleep(3)
        
        with Live(console=console, refresh_per_second=1, transient=False) as live:
            while True:
                try:
                    live.update(self.render_dashboard())
                except Exception as e:
                    console.print(f"[red]Display error: {e}[/red]")
                await asyncio.sleep(config.REFRESH)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Polymarket Multi-Timeframe Trading Bot")
    parser.add_argument("--dry-run", action="store_true", help="Show signals without trading")
    parser.add_argument("--paper", action="store_true", help="Paper trading (simulated orders)")
    parser.add_argument("--coins", type=str, default="BTC", help="Coins to trade (comma-separated)")
    args = parser.parse_args()
    
    console.print("\n[bold magenta]═══════════════════════════════════════════════════════════════[/bold magenta]")
    console.print("[bold magenta]     POLYMARKET MULTI-TIMEFRAME AUTO TRADING BOT              [/bold magenta]")
    console.print("[bold magenta]     Trading: 15-minute + 1-hour timeframes                   [/bold magenta]")
    console.print("[bold magenta]═══════════════════════════════════════════════════════════════[/bold magenta]\n")
    
    if args.dry_run:
        console.print("[yellow]🔒 DRY RUN MODE - No orders will be placed[/yellow]\n")
    elif args.paper:
        console.print("[blue]📝 PAPER TRADING MODE - Orders are simulated[/blue]\n")
    else:
        console.print("[green]💰 LIVE TRADING MODE - Real orders will be placed![/green]\n")
    
    # Parse coins
    coins = [c.strip().upper() for c in args.coins.split(",")]
    for coin in coins:
        if coin not in config.COINS:
            console.print(f"[red]Invalid coin: {coin}. Supported: {config.COINS}[/red]")
            return
    
    # Fixed timeframes: 15m and 1h
    timeframes = ["15m", "1h"]
    
    console.print(f"[bold]Coins:[/bold] {', '.join(coins)}")
    console.print(f"[bold]Timeframes:[/bold] {', '.join(timeframes)}\n")
    
    # Create and initialize bot
    bot = MultiTimeframeBot(
        coins=coins,
        timeframes=timeframes,
        dry_run=args.dry_run,
        paper=args.paper
    )
    
    if not await bot.initialize():
        console.print("[red]Failed to initialize bot. Check your credentials in .env[/red]")
        return
    
    console.print("\n[bold]Starting data feeds and trading loop...[/bold]\n")
    
    # Run all async tasks
    await asyncio.gather(
        bot.run_binance_feeds(),
        bot.run_pm_feeds(),
        bot.trading_loop(),
        bot.display_loop(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
