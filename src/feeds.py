"""
Data feeds module for Polymarket Trading Bot.
Handles Binance and Polymarket WebSocket/REST data streams.
"""
import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Optional

import requests
import websockets

from . import config


@dataclass
class State:
    """Centralized state for all market data."""
    # Order book
    bids: list[tuple[float, float]] = field(default_factory=list)
    asks: list[tuple[float, float]] = field(default_factory=list)
    mid: float = 0.0
    
    # Trades
    trades: list[dict] = field(default_factory=list)
    
    # Klines (candles)
    klines: list[dict] = field(default_factory=list)
    cur_kline: Optional[dict] = None
    
    # Polymarket tokens
    pm_up_id: Optional[str] = None
    pm_dn_id: Optional[str] = None
    pm_up: Optional[float] = None
    pm_dn: Optional[float] = None
    
    # Market expiry tracking
    market_expiry_ts: Optional[float] = None  # Unix timestamp when market resolves
    market_slug: Optional[str] = None  # Current market slug
    
    # Connection status
    binance_connected: bool = False
    pm_connected: bool = False
    
    def is_near_expiry(self) -> bool:
        """Check if we are approaching market expiry."""
        if self.market_expiry_ts is None:
            return False
        time_remaining = self.market_expiry_ts - time.time()
        return time_remaining <= config.EXIT_BEFORE_EXPIRY_SECONDS
    
    def seconds_to_expiry(self) -> Optional[float]:
        """Get seconds remaining until market expiry."""
        if self.market_expiry_ts is None:
            return None
        return max(0, self.market_expiry_ts - time.time())


OB_POLL_INTERVAL = 2


async def ob_poller(symbol: str, state: State):
    """Poll Binance order book every 2 seconds."""
    url = f"{config.BINANCE_REST}/depth"
    print(f"  [Binance OB] polling {symbol} every {OB_POLL_INTERVAL}s")
    while True:
        try:
            resp = requests.get(
                url, 
                params={"symbol": symbol, "limit": config.OB_LEVELS}, 
                timeout=3
            ).json()
            state.bids = [(float(p), float(q)) for p, q in resp["bids"]]
            state.asks = [(float(p), float(q)) for p, q in resp["asks"]]
            if state.bids and state.asks:
                state.mid = (state.bids[0][0] + state.asks[0][0]) / 2
        except Exception as e:
            print(f"  [Binance OB] error: {e}")
        await asyncio.sleep(OB_POLL_INTERVAL)


async def binance_feed(symbol: str, kline_iv: str, state: State):
    """Connect to Binance WebSocket for trades and klines."""
    sym = symbol.lower()
    streams = "/".join([
        f"{sym}@trade",
        f"{sym}@kline_{kline_iv}",
    ])
    url = f"{config.BINANCE_WS}?streams={streams}"
    
    while True:
        try:
            async with websockets.connect(url, ping_interval=20) as ws:
                print(f"  [Binance WS] connected – {symbol}")
                state.binance_connected = True
                
                while True:
                    data = json.loads(await ws.recv())
                    stream = data.get("stream", "")
                    pay = data["data"]
                    
                    if "@trade" in stream:
                        state.trades.append({
                            "t": pay["T"] / 1000.0,
                            "price": float(pay["p"]),
                            "qty": float(pay["q"]),
                            "is_buy": not pay["m"],
                        })
                        # Cleanup old trades
                        if len(state.trades) > 5000:
                            cut = time.time() - config.TRADE_TTL
                            state.trades = [t for t in state.trades if t["t"] >= cut]
                    
                    elif "@kline" in stream:
                        k = pay["k"]
                        candle = {
                            "t": k["t"] / 1000.0,
                            "o": float(k["o"]),
                            "h": float(k["h"]),
                            "l": float(k["l"]),
                            "c": float(k["c"]),
                            "v": float(k["v"]),
                        }
                        state.cur_kline = candle
                        if k["x"]:  # Candle closed
                            state.klines.append(candle)
                            state.klines = state.klines[-config.KLINE_MAX:]
                            
        except Exception as e:
            print(f"  [Binance WS] disconnected: {e}, reconnecting...")
            state.binance_connected = False
            await asyncio.sleep(5)


async def bootstrap(symbol: str, interval: str, state: State):
    """Fetch historical candles on startup."""
    try:
        resp = requests.get(
            f"{config.BINANCE_REST}/klines",
            params={"symbol": symbol, "interval": interval, "limit": config.KLINE_BOOT},
        ).json()
        state.klines = [
            {
                "t": r[0] / 1e3,
                "o": float(r[1]),
                "h": float(r[2]),
                "l": float(r[3]),
                "c": float(r[4]),
                "v": float(r[5]),
            }
            for r in resp
        ]
        print(f"  [Binance] loaded {len(state.klines)} historical candles")
    except Exception as e:
        print(f"  [Binance] bootstrap failed: {e}")


_MONTHS = ["", "january", "february", "march", "april", "may", "june",
           "july", "august", "september", "october", "november", "december"]


def _et_now() -> datetime:
    """Get current Eastern Time."""
    utc = datetime.now(timezone.utc)
    year = utc.year
    
    # Calculate DST transitions
    mar1_dow = datetime(year, 3, 1).weekday()
    mar_sun = 1 + (6 - mar1_dow) % 7
    dst_start = datetime(year, 3, mar_sun + 7, 2, 0, 0, tzinfo=timezone.utc)
    
    nov1_dow = datetime(year, 11, 1).weekday()
    nov_sun = 1 + (6 - nov1_dow) % 7
    dst_end = datetime(year, 11, nov_sun, 6, 0, 0, tzinfo=timezone.utc)
    
    offset = timedelta(hours=-4) if dst_start <= utc < dst_end else timedelta(hours=-5)
    return utc + offset


def _to_12h(hour24: int) -> str:
    """Convert 24h to 12h format."""
    if hour24 == 0:
        return "12am"
    if hour24 < 12:
        return f"{hour24}am"
    if hour24 == 12:
        return "12pm"
    return f"{hour24 - 12}pm"


def _build_slug(coin: str, tf: str) -> Optional[str]:
    """Build Polymarket market slug for given coin and timeframe."""
    now_utc = datetime.now(timezone.utc)
    now_ts = int(now_utc.timestamp())
    et = _et_now()
    
    if tf == "15m":
        ts = (now_ts // 900) * 900
        return f"{config.COIN_PM[coin]}-updown-15m-{ts}"
    
    if tf == "4h":
        ts = ((now_ts - 3600) // 14400) * 14400 + 3600
        return f"{config.COIN_PM[coin]}-updown-4h-{ts}"
    
    if tf == "1h":
        return (f"{config.COIN_PM_LONG[coin]}-up-or-down-"
                f"{_MONTHS[et.month]}-{et.day}-{_to_12h(et.hour)}-et")
    
    if tf == "daily":
        resolution = et.replace(hour=12, minute=0, second=0, microsecond=0)
        target = et if et < resolution else et + timedelta(days=1)
        return (f"{config.COIN_PM_LONG[coin]}-up-or-down-on-"
                f"{_MONTHS[target.month]}-{target.day}")
    
    return None


def _calculate_expiry_ts(tf: str) -> Optional[float]:
    """Calculate the expiry timestamp for a given timeframe."""
    now_utc = datetime.now(timezone.utc)
    now_ts = int(now_utc.timestamp())
    
    if tf == "15m":
        # Current 15m window ends at the next 15m boundary
        expiry_ts = ((now_ts // 900) + 1) * 900
        return float(expiry_ts)
    
    if tf == "1h":
        # Current hour ends at next hour boundary
        expiry_ts = ((now_ts // 3600) + 1) * 3600
        return float(expiry_ts)
    
    if tf == "4h":
        # 4h windows aligned to specific times
        base = ((now_ts - 3600) // 14400) * 14400 + 3600
        expiry_ts = base + 14400
        return float(expiry_ts)
    
    if tf == "daily":
        # Daily markets resolve at 12 PM ET
        et = _et_now()
        resolution = et.replace(hour=12, minute=0, second=0, microsecond=0)
        if et >= resolution:
            resolution += timedelta(days=1)
        # Convert back to UTC
        utc = datetime.now(timezone.utc)
        offset = et - utc
        return (resolution - offset).timestamp()
    
    return None


def fetch_pm_tokens(coin: str, tf: str, state: Optional[State] = None) -> tuple[Optional[str], Optional[str]]:
    """Fetch Polymarket Up/Down token IDs for given market."""
    slug = _build_slug(coin, tf)
    if slug is None:
        return None, None
    
    try:
        data = requests.get(config.PM_GAMMA, params={"slug": slug, "limit": 1}).json()
        if not data or data[0].get("ticker") != slug:
            print(f"  [PM] no active market for slug: {slug}")
            return None, None
        
        ids = json.loads(data[0]["markets"][0]["clobTokenIds"])
        
        # Update state with market info if provided
        if state:
            state.market_slug = slug
            state.market_expiry_ts = _calculate_expiry_ts(tf)
            if state.market_expiry_ts:
                remaining = state.seconds_to_expiry()
                if remaining:
                    mins = int(remaining // 60)
                    secs = int(remaining % 60)
                    print(f"  [PM] Market expires in {mins}m {secs}s")
        
        return ids[0], ids[1]
    except Exception as e:
        print(f"  [PM] token fetch failed ({slug}): {e}")
        return None, None


async def pm_feed(state: State):
    """Connect to Polymarket WebSocket for price updates."""
    if not state.pm_up_id:
        print("  [PM] no tokens for this coin/timeframe – skipped")
        return
    
    assets = [state.pm_up_id, state.pm_dn_id]
    
    while True:
        try:
            async with websockets.connect(config.PM_WS, ping_interval=20) as ws:
                await ws.send(json.dumps({"assets_ids": assets, "type": "market"}))
                print("  [PM] connected")
                state.pm_connected = True
                
                while True:
                    raw = json.loads(await ws.recv())
                    
                    if isinstance(raw, list):
                        for entry in raw:
                            _pm_apply(entry.get("asset_id"), entry.get("asks", []), state)
                    
                    elif isinstance(raw, dict) and raw.get("event_type") == "price_change":
                        for ch in raw.get("price_changes", []):
                            if ch.get("best_ask"):
                                _pm_set(ch["asset_id"], float(ch["best_ask"]), state)
                                
        except Exception as e:
            print(f"  [PM] disconnected: {e}, reconnecting...")
            state.pm_connected = False
            await asyncio.sleep(5)


def _pm_apply(asset: str, asks: list, state: State):
    """Apply Polymarket order book data."""
    if asks:
        _pm_set(asset, min(float(a["price"]) for a in asks), state)


def _pm_set(asset: str, price: float, state: State):
    """Update Polymarket price state."""
    if asset == state.pm_up_id:
        state.pm_up = price
    elif asset == state.pm_dn_id:
        state.pm_dn = price


async def refresh_market_tokens(coin: str, tf: str, state: State):
    """
    Periodically check for new market when current one expires.
    This is important for 15m markets that roll over frequently.
    """
    while True:
        try:
            if state.is_near_expiry():
                print("  [PM] Market expiring soon, will fetch new tokens after reset")
            
            # Wait for market to reset (check every minute for 15m markets)
            await asyncio.sleep(60)
            
            # Check if we need to refresh tokens
            if state.market_expiry_ts and time.time() > state.market_expiry_ts:
                print("  [PM] Market expired, fetching new tokens...")
                up_id, dn_id = fetch_pm_tokens(coin, tf, state)
                if up_id:
                    state.pm_up_id = up_id
                    state.pm_dn_id = dn_id
                    state.pm_up = None
                    state.pm_dn = None
                    print(f"  [PM] New market: {state.market_slug}")
                    
        except Exception as e:
            print(f"  [PM] Token refresh error: {e}")
            await asyncio.sleep(60)
