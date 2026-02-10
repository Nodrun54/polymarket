"""
Configuration module for Polymarket Trading Bot.
Loads credentials from .env and defines trading parameters.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# ═══════════════════════════════════════════════════════════════════════════
# POLYMARKET API CREDENTIALS
# ═══════════════════════════════════════════════════════════════════════════
POLYMARKET_HOST = "https://clob.polymarket.com"
POLYMARKET_CHAIN_ID = 137  # Polygon

POLYMARKET_API_KEY = os.getenv("POLYMARKET_API_KEY", "")
POLYMARKET_SECRET = os.getenv("POLYMARKET_SECRET", "")
POLYMARKET_PASSPHRASE = os.getenv("POLYMARKET_PASSPHRASE", "")
POLYMARKET_PRIVATE_KEY = os.getenv("POLYMARKET_PRIVATE_KEY", "")
POLYMARKET_FUNDER = os.getenv("POLYMARKET_FUNDER", "")

# Signature type: 0=EOA, 1=Email/Magic, 2=Browser proxy
SIGNATURE_TYPE = 0

# ═══════════════════════════════════════════════════════════════════════════
# SUPPORTED COINS AND TIMEFRAMES
# ═══════════════════════════════════════════════════════════════════════════
COINS = ["BTC", "ETH", "SOL", "XRP"]

COIN_BINANCE = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "XRP": "XRPUSDT",
}

COIN_PM = {"BTC": "btc", "ETH": "eth", "SOL": "sol", "XRP": "xrp"}
COIN_PM_LONG = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "xrp"}

TIMEFRAMES = ["15m", "1h", "4h", "daily"]

# Binance kline interval for each timeframe
TF_KLINE = {"15m": "1m", "1h": "1m", "4h": "15m", "daily": "1h"}

# ═══════════════════════════════════════════════════════════════════════════
# TRADING PARAMETERS - Smart Bot Settings
# ═══════════════════════════════════════════════════════════════════════════
POSITION_SIZE_USD = float(os.getenv("POSITION_SIZE_USD", "3"))
MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "2"))
SIGNAL_CONFIDENCE_THRESHOLD = int(os.getenv("SIGNAL_CONFIDENCE_THRESHOLD", "4"))
TRADE_COOLDOWN_SECONDS = int(os.getenv("TRADE_COOLDOWN_SECONDS", "30"))
DAILY_LOSS_LIMIT_PCT = float(os.getenv("DAILY_LOSS_LIMIT_PCT", "20"))

# ═══════════════════════════════════════════════════════════════════════════
# RISK MANAGEMENT - Stop Loss (10-15%)
# ═══════════════════════════════════════════════════════════════════════════
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "12"))  # 12% stop loss
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "30"))  # Legacy - use FULL_TAKE_PROFIT_PCT
# DAILY_LOSS_LIMIT_PCT and TRADE_COOLDOWN_SECONDS are now defined under TRADING PARAMETERS - Smart Bot Settings
# and are removed from here to avoid duplication and potential confusion.

# ═══════════════════════════════════════════════════════════════════════════
# PROFIT BOOKING - Dynamic Range (25-85%)
# ═══════════════════════════════════════════════════════════════════════════
TRAILING_STOP_PCT = float(os.getenv("TRAILING_STOP_PCT", "8"))
PARTIAL_PROFIT_PCT = float(os.getenv("PARTIAL_PROFIT_PCT", "25"))  # Min profit target
FULL_TAKE_PROFIT_PCT = float(os.getenv("FULL_TAKE_PROFIT_PCT", "50"))  # Mid target
MAX_PROFIT_TARGET_PCT = float(os.getenv("MAX_PROFIT_TARGET_PCT", "85"))  # Max target

# ═══════════════════════════════════════════════════════════════════════════
# RSI-BASED PROFIT BOOKING (Aggressive for oversold buys)
# ═══════════════════════════════════════════════════════════════════════════
RSI_PARTIAL_PROFIT_PCT = float(os.getenv("RSI_PARTIAL_PROFIT_PCT", "15"))
RSI_FULL_TAKE_PROFIT_PCT = float(os.getenv("RSI_FULL_TAKE_PROFIT_PCT", "35"))
RSI_TRAILING_STOP_PCT = float(os.getenv("RSI_TRAILING_STOP_PCT", "5"))

# ═══════════════════════════════════════════════════════════════════════════
# DYNAMIC POSITION SIZING ($1-5 range)
# ═══════════════════════════════════════════════════════════════════════════
MIN_POSITION_SIZE_USD = float(os.getenv("MIN_POSITION_SIZE_USD", "1"))
MAX_POSITION_SIZE_USD = float(os.getenv("MAX_POSITION_SIZE_USD", "5"))

# ═══════════════════════════════════════════════════════════════════════════
# MARKET TIMING - Minimum time before expiry to trade
# ═══════════════════════════════════════════════════════════════════════════
EXIT_BEFORE_EXPIRY_SECONDS = int(os.getenv("EXIT_BEFORE_EXPIRY_SECONDS", "60"))
MAX_POSITION_AGE_HOURS = int(os.getenv("MAX_POSITION_AGE_HOURS", "4"))
MIN_TIME_15M_SECONDS = int(os.getenv("MIN_TIME_15M_SECONDS", "420"))  # 7 minutes
MIN_TIME_1H_SECONDS = int(os.getenv("MIN_TIME_1H_SECONDS", "600"))    # 10 minutes

# ═══════════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════════
DATABASE_FILE = os.getenv("DATABASE_FILE", "polymarket_trades.db")

# ═══════════════════════════════════════════════════════════════════════════
# API RETRY SETTINGS
# ═══════════════════════════════════════════════════════════════════════════
API_RETRY_COUNT = int(os.getenv("API_RETRY_COUNT", "3"))
API_RETRY_DELAY = float(os.getenv("API_RETRY_DELAY", "2"))

# ═══════════════════════════════════════════════════════════════════════════
# AUTO TRADING
# ═══════════════════════════════════════════════════════════════════════════
AUTO_TRADE_ENABLED = os.getenv("AUTO_TRADE_ENABLED", "true").lower() == "true"

# ═══════════════════════════════════════════════════════════════════════════
# BINANCE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════
BINANCE_WS = "wss://stream.binance.com/stream"
BINANCE_REST = "https://api.binance.com/api/v3"
OB_LEVELS = 20
TRADE_TTL = 600  # Keep 10 min of trades
KLINE_MAX = 150  # Max candles in memory
KLINE_BOOT = 100  # Candles fetched on startup

# ═══════════════════════════════════════════════════════════════════════════
# POLYMARKET ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════
PM_GAMMA = "https://gamma-api.polymarket.com/events"
PM_WS = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

# ═══════════════════════════════════════════════════════════════════════════
# ORDER BOOK INDICATORS
# ═══════════════════════════════════════════════════════════════════════════
OBI_BAND_PCT = 1.0  # % band around mid for OBI calc
OBI_THRESH = 0.10   # ±10% = signal
WALL_MULT = 5       # Wall = level qty > N × avg level qty
DEPTH_BANDS = [0.1, 0.5, 1.0]  # % from mid for depth calc

# ═══════════════════════════════════════════════════════════════════════════
# FLOW INDICATORS
# ═══════════════════════════════════════════════════════════════════════════
CVD_WINDOWS = [60, 180, 300]  # 1m / 3m / 5m in seconds
DELTA_WINDOW = 60  # Short delta window (seconds)

# ═══════════════════════════════════════════════════════════════════════════
# TECHNICAL ANALYSIS INDICATORS
# ═══════════════════════════════════════════════════════════════════════════
RSI_PERIOD = 14
RSI_OB = 70  # Overbought
RSI_OS = 30  # Oversold
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIG = 9
EMA_S = 5
EMA_L = 20

# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════
HA_COUNT = 8   # Heikin Ashi candles shown
VP_BINS = 30   # Volume profile price buckets
VP_SHOW = 9    # VP rows visible
REFRESH = 10   # Seconds between dashboard redraws

# ═══════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════
TRADE_LOG_FILE = os.getenv("TRADE_LOG_FILE", "trades.csv")


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

def validate_config(require_credentials: bool = True) -> tuple[bool, list[str]]:
    """
    Validate configuration settings.
    
    Args:
        require_credentials: If True, validates that API credentials are set
    
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    
    # Check credentials if required (skip for dry-run/paper modes)
    if require_credentials:
        if not POLYMARKET_PRIVATE_KEY or POLYMARKET_PRIVATE_KEY == "your_private_key_here":
            errors.append("POLYMARKET_PRIVATE_KEY is not set in .env file")
        
        if not POLYMARKET_FUNDER or POLYMARKET_FUNDER == "your_funder_address_here":
            errors.append("POLYMARKET_FUNDER is not set in .env file")
        
        if POLYMARKET_PRIVATE_KEY and not POLYMARKET_PRIVATE_KEY.startswith("0x"):
            errors.append("POLYMARKET_PRIVATE_KEY should start with '0x'")
        
        if POLYMARKET_FUNDER and not POLYMARKET_FUNDER.startswith("0x"):
            errors.append("POLYMARKET_FUNDER should start with '0x'")
    
    # Validate numeric ranges
    if not (0 <= STOP_LOSS_PCT <= 100):
        errors.append(f"STOP_LOSS_PCT ({STOP_LOSS_PCT}) must be between 0 and 100")
    
    if not (0 <= PROFIT_TARGET_PCT <= 1000):
        errors.append(f"PROFIT_TARGET_PCT ({PROFIT_TARGET_PCT}) must be between 0 and 1000")
    
    if MAX_DAILY_LOSS_USD < 0:
        errors.append(f"MAX_DAILY_LOSS_USD ({MAX_DAILY_LOSS_USD}) cannot be negative")
    
    if POSITION_SIZE_USD <= 0:
        errors.append(f"POSITION_SIZE_USD ({POSITION_SIZE_USD}) must be positive")
    
    if MAX_POSITIONS <= 0:
        errors.append(f"MAX_POSITIONS ({MAX_POSITIONS}) must be positive")
    
    return (len(errors) == 0, errors)


def print_config_errors(errors: list[str]):
    """Print configuration errors in a user-friendly format."""
    print("\n" + "="*70)
    print("⚠️  CONFIGURATION ERRORS")
    print("="*70)
    for i, error in enumerate(errors, 1):
        print(f"  {i}. {error}")
    print("\nPlease fix these errors in your .env file and try again.")
    print("See .env.example for reference.")
    print("="*70 + "\n")
