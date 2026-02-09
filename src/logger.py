"""
Trade logging module for Polymarket Trading Bot.
Logs all trade entries and exits to CSV for analysis.
"""
import csv
import os
from datetime import datetime
from typing import Optional
from . import config


class TradeLogger:
    """Handles logging of all trades to CSV file."""
    
    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file or config.TRADE_LOG_FILE
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create log file with headers if it doesn't exist."""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'action',
                    'token_id',
                    'side',
                    'shares',
                    'price',
                    'size_usd',
                    'pnl',
                    'pnl_pct',
                    'reason',
                    'confidence',
                    'signal_direction',
                    'order_id'
                ])
    
    def log_entry(
        self,
        token_id: str,
        side: str,
        shares: float,
        price: float,
        size_usd: float,
        confidence: int,
        signal_direction: str,
        order_id: str = ""
    ):
        """Log a trade entry (buy)."""
        self._write_row({
            'timestamp': datetime.now().isoformat(),
            'action': 'BUY',
            'token_id': token_id,
            'side': side,
            'shares': shares,
            'price': price,
            'size_usd': size_usd,
            'pnl': 0,
            'pnl_pct': 0,
            'reason': 'signal',
            'confidence': confidence,
            'signal_direction': signal_direction,
            'order_id': order_id
        })
    
    def log_exit(
        self,
        token_id: str,
        side: str,
        shares: float,
        entry_price: float,
        exit_price: float,
        reason: str,
        order_id: str = ""
    ):
        """Log a trade exit (sell)."""
        pnl = (exit_price - entry_price) * shares
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        size_usd = shares * exit_price
        
        self._write_row({
            'timestamp': datetime.now().isoformat(),
            'action': 'SELL',
            'token_id': token_id,
            'side': side,
            'shares': shares,
            'price': exit_price,
            'size_usd': size_usd,
            'pnl': round(pnl, 4),
            'pnl_pct': round(pnl_pct, 2),
            'reason': reason,
            'confidence': 0,
            'signal_direction': '',
            'order_id': order_id
        })
    
    def log_partial_exit(
        self,
        token_id: str,
        side: str,
        shares: float,
        entry_price: float,
        exit_price: float,
        order_id: str = ""
    ):
        """Log a partial profit exit."""
        self.log_exit(
            token_id=token_id,
            side=side,
            shares=shares,
            entry_price=entry_price,
            exit_price=exit_price,
            reason="partial_profit",
            order_id=order_id
        )
    
    def _write_row(self, data: dict):
        """Write a row to the CSV file."""
        try:
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    data['timestamp'],
                    data['action'],
                    data['token_id'],
                    data['side'],
                    data['shares'],
                    data['price'],
                    data['size_usd'],
                    data['pnl'],
                    data['pnl_pct'],
                    data['reason'],
                    data['confidence'],
                    data['signal_direction'],
                    data['order_id']
                ])
        except Exception as e:
            print(f"  [Logger] Failed to write trade log: {e}")
    
    def get_daily_stats(self) -> dict:
        """Get trading statistics for today."""
        today = datetime.now().date().isoformat()
        stats = {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0
        }
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['timestamp'].startswith(today) and row['action'] == 'SELL':
                        stats['trades'] += 1
                        pnl = float(row['pnl'])
                        stats['total_pnl'] += pnl
                        
                        if pnl > 0:
                            stats['wins'] += 1
                        elif pnl < 0:
                            stats['losses'] += 1
                        
                        stats['best_trade'] = max(stats['best_trade'], pnl)
                        stats['worst_trade'] = min(stats['worst_trade'], pnl)
        except Exception:
            pass
        
        return stats
    
    def get_recent_trades(self, count: int = 10) -> list:
        """Get the most recent trades."""
        trades = []
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                trades = list(reader)
        except Exception:
            pass
        
        return trades[-count:] if trades else []
