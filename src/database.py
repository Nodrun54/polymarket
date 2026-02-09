"""
SQLite database module for Polymarket Trading Bot.
Handles persistent storage of trades, positions, and daily statistics.
"""
import sqlite3
import os
import time
from datetime import datetime, date
from typing import Optional, List
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from . import config


# Database file path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                       getattr(config, 'DATABASE_FILE', 'polymarket_trades.db'))


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize database tables if they don't exist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Trades table - all executed trades
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                token_id TEXT NOT NULL,
                side TEXT NOT NULL,
                shares REAL NOT NULL,
                price REAL NOT NULL,
                size_usd REAL NOT NULL,
                pnl REAL DEFAULT 0,
                pnl_pct REAL DEFAULT 0,
                reason TEXT,
                confidence INTEGER DEFAULT 0,
                signal_direction TEXT,
                order_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Active positions table - for recovery on restart
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                token_id TEXT PRIMARY KEY,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                size_usd REAL NOT NULL,
                shares REAL NOT NULL,
                entry_time REAL NOT NULL,
                order_id TEXT,
                highest_price REAL DEFAULT 0,
                partial_sold INTEGER DEFAULT 0,
                original_shares REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Daily statistics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                total_trades INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                best_trade REAL DEFAULT 0,
                worst_trade REAL DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_action ON trades(action)")
        
        # Learned patterns table - for self-learning
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        print(f"  [Database] Initialized at {DB_PATH}")


class TradeDatabase:
    """Handles all database operations for trades and positions."""
    
    def __init__(self):
        init_database()
    
    # ═══════════════════════════════════════════════════════════════════════
    # TRADE LOGGING
    # ═══════════════════════════════════════════════════════════════════════
    
    def log_entry(
        self,
        token_id: str,
        side: str,
        shares: float,
        price: float,
        size_usd: float,
        confidence: int = 0,
        signal_direction: str = "",
        order_id: str = ""
    ) -> int:
        """Log a trade entry (buy). Returns the trade ID."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (timestamp, action, token_id, side, shares, price, 
                                   size_usd, pnl, pnl_pct, reason, confidence, 
                                   signal_direction, order_id)
                VALUES (?, 'BUY', ?, ?, ?, ?, ?, 0, 0, 'signal', ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                token_id, side, shares, price, size_usd,
                confidence, signal_direction, order_id
            ))
            return cursor.lastrowid
    
    def log_exit(
        self,
        token_id: str,
        side: str,
        shares: float,
        entry_price: float,
        exit_price: float,
        reason: str,
        order_id: str = ""
    ) -> int:
        """Log a trade exit (sell). Returns the trade ID."""
        pnl = (exit_price - entry_price) * shares
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        size_usd = shares * exit_price
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (timestamp, action, token_id, side, shares, price,
                                   size_usd, pnl, pnl_pct, reason, order_id)
                VALUES (?, 'SELL', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                token_id, side, shares, exit_price, size_usd,
                round(pnl, 4), round(pnl_pct, 2), reason, order_id
            ))
            
            # Update daily stats
            self._update_daily_stats(pnl)
            
            return cursor.lastrowid
    
    def log_partial_exit(
        self,
        token_id: str,
        side: str,
        shares: float,
        entry_price: float,
        exit_price: float,
        order_id: str = ""
    ) -> int:
        """Log a partial profit exit."""
        return self.log_exit(
            token_id=token_id,
            side=side,
            shares=shares,
            entry_price=entry_price,
            exit_price=exit_price,
            reason="partial_profit",
            order_id=order_id
        )
    
    # ═══════════════════════════════════════════════════════════════════════
    # POSITION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def save_position(
        self,
        token_id: str,
        side: str,
        entry_price: float,
        size_usd: float,
        shares: float,
        entry_time: float,
        order_id: str = "",
        highest_price: float = 0,
        partial_sold: bool = False,
        original_shares: float = 0
    ):
        """Save or update an active position."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO positions 
                (token_id, side, entry_price, size_usd, shares, entry_time, 
                 order_id, highest_price, partial_sold, original_shares)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                token_id, side, entry_price, size_usd, shares, entry_time,
                order_id, highest_price or entry_price, 
                1 if partial_sold else 0,
                original_shares or shares
            ))
    
    def remove_position(self, token_id: str):
        """Remove a position from active positions."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM positions WHERE token_id = ?", (token_id,))
    
    def get_all_positions(self) -> List[dict]:
        """Get all active positions for recovery on restart."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM positions")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def clear_all_positions(self):
        """Clear all active positions."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM positions")
    
    def update_highest_price(self, token_id: str, highest_price: float):
        """Update the highest price seen for a position."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE positions SET highest_price = ? 
                WHERE token_id = ? AND highest_price < ?
            """, (highest_price, token_id, highest_price))
    
    def mark_partial_sold(self, token_id: str, remaining_shares: float, remaining_usd: float):
        """Mark a position as having taken partial profit."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE positions SET partial_sold = 1, shares = ?, size_usd = ?
                WHERE token_id = ?
            """, (remaining_shares, remaining_usd, token_id))
    
    # ═══════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════
    
    def _update_daily_stats(self, pnl: float):
        """Update daily statistics after a trade exit."""
        today = date.today().isoformat()
        
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current stats
            cursor.execute("SELECT * FROM daily_stats WHERE date = ?", (today,))
            row = cursor.fetchone()
            
            if row:
                # Update existing
                stats = dict(row)
                stats['total_trades'] += 1
                if pnl > 0:
                    stats['wins'] += 1
                elif pnl < 0:
                    stats['losses'] += 1
                stats['total_pnl'] += pnl
                stats['best_trade'] = max(stats['best_trade'], pnl)
                stats['worst_trade'] = min(stats['worst_trade'], pnl)
                
                cursor.execute("""
                    UPDATE daily_stats SET 
                        total_trades = ?, wins = ?, losses = ?,
                        total_pnl = ?, best_trade = ?, worst_trade = ?,
                        updated_at = ?
                    WHERE date = ?
                """, (
                    stats['total_trades'], stats['wins'], stats['losses'],
                    stats['total_pnl'], stats['best_trade'], stats['worst_trade'],
                    datetime.now().isoformat(), today
                ))
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO daily_stats (date, total_trades, wins, losses, 
                                            total_pnl, best_trade, worst_trade)
                    VALUES (?, 1, ?, ?, ?, ?, ?)
                """, (
                    today,
                    1 if pnl > 0 else 0,
                    1 if pnl < 0 else 0,
                    pnl,
                    max(0, pnl),
                    min(0, pnl)
                ))
    
    def get_daily_stats(self, target_date: Optional[str] = None) -> dict:
        """Get trading statistics for a specific date (default: today)."""
        target_date = target_date or date.today().isoformat()
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_stats WHERE date = ?", (target_date,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return {
                'date': target_date,
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'total_pnl': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0
            }
    
    def get_recent_trades(self, count: int = 10) -> List[dict]:
        """Get the most recent trades."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades ORDER BY id DESC LIMIT ?
            """, (count,))
            rows = cursor.fetchall()
            return [dict(row) for row in reversed(rows)]
    
    def get_all_time_stats(self) -> dict:
        """Get overall trading statistics."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                    COALESCE(SUM(pnl), 0) as total_pnl,
                    COALESCE(MAX(pnl), 0) as best_trade,
                    COALESCE(MIN(pnl), 0) as worst_trade
                FROM trades WHERE action = 'SELL'
            """)
            row = cursor.fetchone()
            return dict(row) if row else {}
    
    # ═══════════════════════════════════════════════════════════════════════
    # SELF-LEARNING DATA
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_learned_patterns(self) -> Optional[dict]:
        """Get saved learned patterns from database."""
        import json
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM learned_patterns ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row['data'])
                except:
                    return None
        return None
    
    def save_learned_patterns(self, patterns: dict):
        """Save learned patterns to database."""
        import json
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO learned_patterns (data, updated_at)
                VALUES (?, ?)
            """, (json.dumps(patterns), datetime.now().isoformat()))


# Global database instance
_db_instance: Optional[TradeDatabase] = None


def get_database() -> TradeDatabase:
    """Get the global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = TradeDatabase()
    return _db_instance
