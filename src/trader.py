"""
Trading execution module for Polymarket Trading Bot.
Handles order creation, execution, position management, and profit booking via Polymarket CLOB API.
"""
import time
from typing import Optional
from dataclasses import dataclass

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import (
    MarketOrderArgs, 
    OrderArgs, 
    OrderType,
    OpenOrderParams,
    ApiCreds,
)
from py_clob_client.order_builder.constants import BUY, SELL

from . import config
from .risk import Position, RiskManager
from .database import get_database, TradeDatabase


@dataclass
class TradeResult:
    """Result of a trade execution."""
    success: bool
    order_id: Optional[str] = None
    filled_price: Optional[float] = None
    filled_shares: Optional[float] = None
    error: Optional[str] = None


class Trader:
    """Handles all trading operations via Polymarket CLOB API with profit booking."""
    
    def __init__(self, dry_run: bool = False, paper: bool = False):
        self.dry_run = dry_run
        self.paper = paper
        self.client: Optional[ClobClient] = None
        self.risk = RiskManager()
        self.db: TradeDatabase = get_database()
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize the CLOB client with credentials."""
        if self.dry_run:
            print("  [Trader] DRY RUN mode - no orders will be placed")
            self._initialized = True
            return True
        
        if self.paper:
            print("  [Trader] PAPER TRADING mode - simulating orders")
            self._initialized = True
            return True
        
        # Check for required credentials
        if not config.POLYMARKET_PRIVATE_KEY or config.POLYMARKET_PRIVATE_KEY == "your_private_key_here":
            print("  [Trader] ERROR: POLYMARKET_PRIVATE_KEY not set in .env")
            return False
        
        if not config.POLYMARKET_FUNDER or config.POLYMARKET_FUNDER == "your_funder_address_here":
            print("  [Trader] ERROR: POLYMARKET_FUNDER not set in .env")
            return False
        
        try:
            self.client = ClobClient(
                config.POLYMARKET_HOST,
                key=config.POLYMARKET_PRIVATE_KEY,
                chain_id=config.POLYMARKET_CHAIN_ID,
                signature_type=config.SIGNATURE_TYPE,
                funder=config.POLYMARKET_FUNDER,
            )
            
            # Set API credentials
            if config.POLYMARKET_API_KEY and config.POLYMARKET_SECRET:
                # Use provided API creds
                creds = ApiCreds(
                    api_key=config.POLYMARKET_API_KEY,
                    api_secret=config.POLYMARKET_SECRET,
                    api_passphrase=config.POLYMARKET_PASSPHRASE,
                )
                self.client.set_api_creds(creds)
            else:
                # Derive new creds
                self.client.set_api_creds(self.client.create_or_derive_api_creds())
            
            # Test connection
            ok = self.client.get_ok()
            if ok:
                print(f"  [Trader] Connected to Polymarket CLOB")
                self._initialized = True
                return True
            else:
                print("  [Trader] Failed to connect to Polymarket CLOB")
                return False
                
        except Exception as e:
            print(f"  [Trader] Initialization failed: {e}")
            return False
    
    def get_midpoint(self, token_id: str) -> Optional[float]:
        """Get current midpoint price for a token."""
        if not self._initialized:
            return None
        if self.dry_run or self.paper:
            return 0.5  # Default for simulation
        
        try:
            return float(self.client.get_midpoint(token_id))
        except Exception as e:
            print(f"  [Trader] Failed to get midpoint: {e}")
            return None
    
    def get_price(self, token_id: str, side: str = "BUY") -> Optional[float]:
        """Get current price for a token."""
        if not self._initialized:
            return None
        if self.dry_run or self.paper:
            return 0.5  # Default for simulation
        
        try:
            return float(self.client.get_price(token_id, side=side))
        except Exception as e:
            print(f"  [Trader] Failed to get price: {e}")
            return None
    
    def calculate_position_size(self, confidence: int) -> float:
        """Calculate position size based on signal confidence."""
        return self.risk.calculate_position_size(confidence)
    
    def buy_market(
        self, 
        token_id: str, 
        amount_usd: float, 
        side: str = "UP",
        confidence: int = 0,
        signal_direction: str = "",
        rsi_triggered: bool = False
    ) -> TradeResult:
        """
        Execute a market buy order with dynamic position sizing.
        
        Args:
            token_id: The outcome token to buy
            amount_usd: USD amount to spend (may be overridden by dynamic sizing)
            side: "UP" or "DOWN" (for logging)
            confidence: Signal confidence for dynamic sizing
            signal_direction: Signal direction for logging
            rsi_triggered: If True, use aggressive RSI profit booking
        """
        market_id = token_id[:16]  # Use truncated ID for cooldown tracking
        
        # Use dynamic position sizing if confidence provided
        if confidence > 0:
            amount_usd = self.calculate_position_size(confidence)
        
        # Validate trade
        if not self.risk.can_open_position:
            reason = f"Max positions ({config.MAX_POSITIONS}) reached"
            return TradeResult(success=False, error=reason)
        
        if not self.risk.can_trade_market(market_id):
            remaining = config.TRADE_COOLDOWN_SECONDS - (time.time() - self.risk.last_trade_time.get(market_id, 0))
            reason = f"Cooldown: {remaining:.0f}s"
            return TradeResult(success=False, error=reason)
        
        # Dry run - just log
        if self.dry_run:
            print(f"  [DRY RUN] Would buy ${amount_usd:.2f} of {side} ({token_id[:16]}...)")
            return TradeResult(success=True, order_id="dry-run", filled_price=0.5, filled_shares=amount_usd * 2)
        
        # Paper trading - simulate
        if self.paper:
            simulated_price = 0.5
            simulated_shares = amount_usd / simulated_price
            print(f"  [PAPER] Simulated buy ${amount_usd:.2f} of {side} at {simulated_price}")
            
            position = Position(
                token_id=token_id,
                side=side,
                entry_price=simulated_price,
                size_usd=amount_usd,
                shares=simulated_shares,
                entry_time=time.time(),
                order_id="paper-" + str(int(time.time())),
                rsi_triggered=rsi_triggered,
            )
            self.risk.add_position(position)
            self.risk.record_trade(market_id)
            
            # Log the trade
            self.db.log_entry(
                token_id=token_id,
                side=side,
                shares=simulated_shares,
                price=simulated_price,
                size_usd=amount_usd,
                confidence=confidence,
                signal_direction=signal_direction,
                order_id=position.order_id
            )
            
            # Save position to database
            self.db.save_position(
                token_id=token_id,
                side=side,
                entry_price=simulated_price,
                size_usd=amount_usd,
                shares=simulated_shares,
                entry_time=position.entry_time,
                order_id=position.order_id
            )
            
            return TradeResult(
                success=True, 
                order_id=position.order_id, 
                filled_price=simulated_price, 
                filled_shares=simulated_shares
            )
        
        # Live trading
        try:
            order = MarketOrderArgs(
                token_id=token_id,
                amount=amount_usd,
                side=BUY,
                order_type=OrderType.FOK,
            )
            
            signed = self.client.create_market_order(order)
            resp = self.client.post_order(signed, OrderType.FOK)
            
            if resp and resp.get("success"):
                order_id = resp.get("orderID", "unknown")
                
                # Get fill info (approximate)
                filled_price = self.get_price(token_id) or 0.5
                filled_shares = amount_usd / filled_price if filled_price > 0 else 0
                
                position = Position(
                    token_id=token_id,
                    side=side,
                    entry_price=filled_price,
                    size_usd=amount_usd,
                    shares=filled_shares,
                    entry_time=time.time(),
                    order_id=order_id,
                    rsi_triggered=rsi_triggered,
                )
                self.risk.add_position(position)
                self.risk.record_trade(market_id)
                
                # Log the trade
                self.db.log_entry(
                    token_id=token_id,
                    side=side,
                    shares=filled_shares,
                    price=filled_price,
                    size_usd=amount_usd,
                    confidence=confidence,
                    signal_direction=signal_direction,
                    order_id=order_id
                )
                
                # Save position to database
                self.db.save_position(
                    token_id=token_id,
                    side=side,
                    entry_price=filled_price,
                    size_usd=amount_usd,
                    shares=filled_shares,
                    entry_time=position.entry_time,
                    order_id=order_id
                )
                
                print(f"  [TRADE] Bought ${amount_usd:.2f} of {side} at {filled_price:.4f}")
                return TradeResult(
                    success=True, 
                    order_id=order_id, 
                    filled_price=filled_price, 
                    filled_shares=filled_shares
                )
            else:
                error = resp.get("errorMsg", "Unknown error") if resp else "No response"
                print(f"  [TRADE] Order failed: {error}")
                return TradeResult(success=False, error=error)
                
        except Exception as e:
            print(f"  [TRADE] Exception: {e}")
            return TradeResult(success=False, error=str(e))
    
    def sell_market(self, token_id: str, shares: float, reason: str = "") -> TradeResult:
        """
        Execute a market sell order.
        
        Args:
            token_id: The outcome token to sell
            shares: Number of shares to sell
            reason: Reason for sell (for logging)
        """
        position = self.risk.get_position_for_token(token_id)
        entry_price = position.entry_price if position else 0.5
        side = position.side if position else "UNKNOWN"
        
        if self.dry_run:
            print(f"  [DRY RUN] Would sell {shares:.4f} shares ({reason})")
            return TradeResult(success=True, order_id="dry-run")
        
        if self.paper:
            exit_price = 0.5  # Simulated
            if position:
                pnl = (exit_price - position.entry_price) * shares
                self.risk.update_daily_pnl(pnl)
                self.risk.remove_position(token_id)
                
                # Log the exit
                self.db.log_exit(
                    token_id=token_id,
                    side=side,
                    shares=shares,
                    entry_price=position.entry_price,
                    exit_price=exit_price,
                    reason=reason,
                    order_id="paper-sell"
                )
                
                # Remove position from database
                self.db.remove_position(token_id)
                
                print(f"  [PAPER] Simulated sell at {exit_price}, P&L: ${pnl:.2f} ({reason})")
            return TradeResult(success=True, order_id="paper-sell", filled_price=exit_price)
        
        # Live trading
        try:
            order = MarketOrderArgs(
                token_id=token_id,
                amount=shares,  # For sells, this is shares
                side=SELL,
                order_type=OrderType.FOK,
            )
            
            signed = self.client.create_market_order(order)
            resp = self.client.post_order(signed, OrderType.FOK)
            
            if resp and resp.get("success"):
                exit_price = self.get_price(token_id, side="SELL") or 0.5
                
                if position:
                    pnl = (exit_price - position.entry_price) * shares
                    self.risk.update_daily_pnl(pnl)
                    self.risk.remove_position(token_id)
                    
                    # Log the exit
                    self.db.log_exit(
                        token_id=token_id,
                        side=side,
                        shares=shares,
                        entry_price=position.entry_price,
                        exit_price=exit_price,
                        reason=reason,
                        order_id=resp.get("orderID", "")
                    )
                    
                    # Remove position from database
                    self.db.remove_position(token_id)
                    
                    print(f"  [TRADE] Sold at {exit_price:.4f}, P&L: ${pnl:.2f} ({reason})")
                
                return TradeResult(success=True, order_id=resp.get("orderID"), filled_price=exit_price)
            else:
                error = resp.get("errorMsg", "Unknown error") if resp else "No response"
                return TradeResult(success=False, error=error)
                
        except Exception as e:
            return TradeResult(success=False, error=str(e))
    
    def sell_partial(self, token_id: str, percentage: float = 0.5, reason: str = "partial_profit") -> TradeResult:
        """
        Sell a percentage of a position.
        
        Args:
            token_id: The outcome token to partially sell
            percentage: Fraction of position to sell (0.0-1.0)
            reason: Reason for sell
        """
        position = self.risk.get_position_for_token(token_id)
        if not position:
            return TradeResult(success=False, error="Position not found")
        
        shares_to_sell = position.shares * percentage
        entry_price = position.entry_price
        side = position.side
        
        if self.dry_run:
            print(f"  [DRY RUN] Would sell {shares_to_sell:.4f} shares ({int(percentage*100)}%) ({reason})")
            return TradeResult(success=True, order_id="dry-run")
        
        if self.paper:
            exit_price = 0.55  # Simulated profit
            pnl = (exit_price - entry_price) * shares_to_sell
            self.risk.update_daily_pnl(pnl)
            self.risk.mark_partial_sold(token_id, shares_to_sell)
            
            # Log the partial exit
            self.db.log_partial_exit(
                token_id=token_id,
                side=side,
                shares=shares_to_sell,
                entry_price=entry_price,
                exit_price=exit_price,
                order_id="paper-partial"
            )
            
            # Update position in database
            pos = self.risk.get_position_for_token(token_id)
            if pos:
                self.db.mark_partial_sold(token_id, pos.shares, pos.size_usd)
            
            print(f"  [PAPER] Partial sell {int(percentage*100)}% at {exit_price}, P&L: ${pnl:.2f}")
            return TradeResult(success=True, order_id="paper-partial", filled_price=exit_price, filled_shares=shares_to_sell)
        
        # Live trading
        try:
            order = MarketOrderArgs(
                token_id=token_id,
                amount=shares_to_sell,
                side=SELL,
                order_type=OrderType.FOK,
            )
            
            signed = self.client.create_market_order(order)
            resp = self.client.post_order(signed, OrderType.FOK)
            
            if resp and resp.get("success"):
                exit_price = self.get_price(token_id, side="SELL") or 0.5
                pnl = (exit_price - entry_price) * shares_to_sell
                self.risk.update_daily_pnl(pnl)
                self.risk.mark_partial_sold(token_id, shares_to_sell)
                
                # Log the partial exit
                self.db.log_partial_exit(
                    token_id=token_id,
                    side=side,
                    shares=shares_to_sell,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    order_id=resp.get("orderID", "")
                )
                
                # Update position in database
                pos = self.risk.get_position_for_token(token_id)
                if pos:
                    self.db.mark_partial_sold(token_id, pos.shares, pos.size_usd)
                
                print(f"  [TRADE] Partial sell {int(percentage*100)}% at {exit_price:.4f}, P&L: ${pnl:.2f}")
                return TradeResult(success=True, order_id=resp.get("orderID"), filled_price=exit_price, filled_shares=shares_to_sell)
            else:
                error = resp.get("errorMsg", "Unknown error") if resp else "No response"
                return TradeResult(success=False, error=error)
                
        except Exception as e:
            return TradeResult(success=False, error=str(e))
    
    def get_open_orders(self) -> list:
        """Get all open orders."""
        if not self._initialized or self.dry_run or self.paper:
            return []
        
        try:
            return self.client.get_orders(OpenOrderParams())
        except Exception as e:
            print(f"  [Trader] Failed to get open orders: {e}")
            return []
    
    def cancel_all_orders(self) -> bool:
        """Cancel all open orders."""
        if not self._initialized or self.dry_run or self.paper:
            return True
        
        try:
            self.client.cancel_all()
            return True
        except Exception as e:
            print(f"  [Trader] Failed to cancel orders: {e}")
            return False
    
    def get_balance(self) -> Optional[float]:
        """Get USDC balance (if available)."""
        if not self._initialized or self.dry_run or self.paper:
            return None
        
        try:
            # Note: py-clob-client may not have direct balance check
            # This would require additional web3 calls
            return None
        except Exception:
            return None
    
    def close_all_positions(self, reason: str = "manual_close") -> list[TradeResult]:
        """Close all open positions."""
        results = []
        for position in list(self.risk.positions):
            result = self.sell_market(position.token_id, position.shares, reason)
            results.append(result)
        return results
    
    def get_daily_stats(self) -> dict:
        """Get trading statistics for today."""
        return self.db.get_daily_stats()
    
    def load_positions_from_db(self) -> int:
        """Load saved positions from database on startup. Returns count of positions loaded."""
        positions = self.db.get_all_positions()
        loaded = 0
        
        for pos_data in positions:
            position = Position(
                token_id=pos_data['token_id'],
                side=pos_data['side'],
                entry_price=pos_data['entry_price'],
                size_usd=pos_data['size_usd'],
                shares=pos_data['shares'],
                entry_time=pos_data['entry_time'],
                order_id=pos_data.get('order_id'),
                highest_price=pos_data.get('highest_price', pos_data['entry_price']),
                partial_sold=bool(pos_data.get('partial_sold', 0)),
                original_shares=pos_data.get('original_shares', pos_data['shares'])
            )
            self.risk.add_position(position)
            loaded += 1
        
        if loaded > 0:
            print(f"  [Trader] Loaded {loaded} positions from database")
        
        return loaded
    
    def save_all_positions(self):
        """Save all positions to database (for graceful shutdown)."""
        for pos in self.risk.positions:
            self.db.save_position(
                token_id=pos.token_id,
                side=pos.side,
                entry_price=pos.entry_price,
                size_usd=pos.size_usd,
                shares=pos.shares,
                entry_time=pos.entry_time,
                order_id=pos.order_id,
                highest_price=pos.highest_price,
                partial_sold=pos.partial_sold,
                original_shares=pos.original_shares
            )
        print(f"  [Trader] Saved {len(self.risk.positions)} positions to database")
