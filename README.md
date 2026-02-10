# 🎰 Polymarket Auto Trading Bot v2.0

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance, automated trading system for [Polymarket](https://polymarket.com) CLOB. This bot leverages 11+ technical indicators, real-time Binance price feeds, and advanced risk management strategies to execute smart trades on prediction markets.

---

## 🚀 Key Features

- **🤖 Full Automation**: Async orchestration for seamless signal generation and trade execution.
- **📊 Terminal Dashboard**: Beautiful, real-time TUI (Terminal User Interface) built with `rich`.
- **📈 Advanced Indicators**:
  - **Order Book**: OBI (Order Book Imbalance), Buy/Sell Walls detection.
  - **Technical**: RSI, MACD, EMA Crossovers, Heikin Ashi streaks.
  - **Flow**: CVD (Cumulative Volume Delta) and short-term Delta analysis.
- **🛡️ Risk Management**:
  - Stop Loss (10-15% default).
  - Trailing Stop-Loss for locking in gains.
  - Partial Profit Booking (50% exit at first target).
  - Market Expiry tracking to avoid illiquid settlement.
- **💾 Trade Persistence**: SQLite integration to recover positions after restarts.
- **🧪 Multi-Mode Execution**: Live, Paper (Simulated), and Dry Run (Signals only) modes.

---

## 🛠️ Tech Stack

- **Core**: Python 3.8+ (Asyncio)
- **API Clients**: `py-clob-client` (Polymarket), `requests`, `aiohttp`
- **Data Feeds**: WebSockets for real-time Binance prices and Polymarket order books.
- **UI**: `rich` for high-fidelity terminal dashboards.
- **Storage**: SQLite for local trade and position tracking.

---

## ⚙️ Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Nodrun54/polymarket.git
   cd polymarket-bot
   ```

2. **Set up Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Create a `.env` file in the root directory (see [Configuration](#-configuration) below).

---

## 🔧 Configuration

The bot is highly configurable via `.env`. Below are the primary settings:

### API Credentials
| Variable | Description |
| :--- | :--- |
| `POLYMARKET_API_KEY` | Your Polymarket CLOB API Key |
| `POLYMARKET_SECRET` | Your Polymarket CLOB Secret |
| `POLYMARKET_PASSPHRASE`| Your Polymarket CLOB Passphrase |
| `POLYMARKET_PRIVATE_KEY`| Your Polygon Wallet Private Key |

### Trading Parameters
| Variable | Default | Description |
| :--- | :--- | :--- |
| `AUTO_TRADE_ENABLED` | `true` | Enable/Disable automated order execution |
| `POSITION_SIZE_USD` | `3` | Default size per trade in USDC |
| `MAX_POSITIONS` | `2` | Maximum concurrent open positions |
| `STOP_LOSS_PCT` | `12` | Percentage drop to trigger a hard stop-loss |
| `PARTIAL_PROFIT_PCT`| `25` | Target for 50% partial profit booking |
| `TRAILING_STOP_PCT` | `8` | Trailing distance for profit protection |

---

## 🏎️ Usage

Run the bot using `main.py`. You can select the coin and timeframe interactively or via CLI arguments.

### Interactive Mode
```bash
python main.py
```

### Direct Execution (BTC 15m)
```bash
python main.py --coin BTC --tf 15m --paper
```

### Command-Line Arguments
- `--dry-run`: View signals and dashboard without placing any orders.
- `--paper`: Simulate trades locally (no funds used).
- `--coin [BTC|ETH|SOL|XRP]`: Specify target asset.
- `--tf [15m|1h|4h|daily]`: Specify candle timeframe.

---

## 📂 Project Structure

- `main.py`: Main orchestration loop and dashboard rendering.
- `src/`:
  - `scanner.py`: Scans markets for opportunities.
  - `signals.py`: Logic for combining indicator data into signals.
  - `trader.py`: handles Order execution and API interaction.
  - `risk.py`: Position management and profit-booking logic.
  - `indicators.py`: TA and Order Book math (RSI, OBI, CVD, etc.).
  - `database.py`: SQLite persistence layer.

---

## ⚠️ Disclaimer

**Financial Risk**: Trading crypto and prediction markets involves significant risk. This bot is provided for educational purposes. Never trade funds you cannot afford to lose. The developers are not responsible for any financial losses incurred.

---
