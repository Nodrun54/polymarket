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
   cd polymarket
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

## 📤 Publishing to GitHub - Complete Guide

This section provides step-by-step instructions for safely publishing your bot to GitHub **without exposing your credentials**.

### ✅ Pre-Publication Checklist

Before pushing to GitHub, verify the following:

1. **Credentials are NOT in your code**:
   ```bash
   # Search for potential API keys or private keys in code
   git grep -i "POLYMARKET_API_KEY"
   git grep -i "0x[a-fA-F0-9]\{64\}"
   ```
   
2. **`.env` file is ignored**:
   ```bash
   git status
   ```
   Result should NOT show `.env` file
   
3. **`.env.example` exists with placeholders only**:
   ```bash
   cat .env.example | grep "your_"
   ```
   Should see placeholder values like `your_api_key_here`
   
4. **`.gitignore` is properly configured**:
   ```bash
   cat .gitignore | grep ".env"
   ```
   Should show `.env` in the list

5. **Database file is excluded** (contains your trade history):
   ```bash
   git status | grep ".db"
   ```
   Should NOT appear (handled by `.gitignore`)

### 📋 Step-by-Step Git Workflow

#### First Time Setup (New Repository)

1. **Initialize Git** (if not already done):
   ```bash
   cd c:/Users/debar/Desktop/polymarket
   git init
   ```

2. **Verify sensitive files are excluded**:
   ```bash
   git status
   ```
   Ensure `.env` and `polymarket_trades.db` are NOT listed

3. **Add safe files to staging**:
   ```bash
   git add .gitignore
   git add .env.example
   git add README.md
   git add requirements.txt
   git add main.py
   git add src/
   ```

4. **Review what will be committed**:
   ```bash
   git status
   git diff --cached
   ```
   **CRITICAL**: If you see any API keys, private keys, or wallet addresses **STOP** and remove them!

5. **Commit changes**:
   ```bash
   git commit -m "Initial commit: Polymarket trading bot with indicators and risk management"
   ```

6. **Create GitHub repository**:
   - Go to [github.com](https://github.com)
   - Click "New repository"
   - Name it (e.g., `polymarket-trading-bot`)
   - **DO NOT** initialize with README (you already have one)
   - Click "Create repository"

7. **Link local repository to GitHub**:
   ```bash
   git remote add origin https://github.com/Nodrun54/polymarket.git
   git branch -M main
   git push -u origin main
   ```

#### Updating Existing Repository

1. **Check current status**:
   ```bash
   git status
   ```

2. **Add only safe files**:
   ```bash
   git add .
   # OR be specific:
   git add README.md
   git add src/config.py
   ```

3. **Verify what will be committed**:
   ```bash
   git diff --cached
   ```

4. **Commit and push**:
   ```bash
   git commit -m "docs: Update README with setup instructions"
   git push
   ```

### 🔐 Security Verification Commands

Run these commands before EVERY push to GitHub:

```bash
# 1. Check no .env file is tracked
git ls-files | grep ".env"
# Expected: No output (or only .env.example)

# 2. Check for hardcoded credentials
git grep -E "(POLYMARKET_API_KEY|POLYMARKET_SECRET|POLYMARKET_PRIVATE_KEY)" -- ':!.env.example'
# Expected: Only configuration file references, no actual values

# 3. Verify .gitignore is working
git check-ignore .env
# Expected: .env

# 4. Check what's about to be pushed
git log origin/main..HEAD
git diff origin/main..HEAD
# Review carefully for any secrets
```

### 🚨 Emergency: Accidentally Committed Secrets

If you accidentally committed credentials:

1. **DO NOT just delete them and commit again** - they're still in git history!

2. **Remove from history** (if not yet pushed):
   ```bash
   # Undo last commit but keep changes
   git reset HEAD~1
   
   # Remove .env from staging if accidentally added
   git reset .env
   
   # Commit again without secrets
   git add .
   git commit -m "Your message"
   ```

3. **If already pushed to GitHub**:
   - **Immediately rotate ALL credentials** (generate new API keys, new wallet)
   - Contact GitHub support to purge sensitive data
   - Consider making repository private temporarily

4. **For complete history cleanup** (ADVANCED):
   ```bash
   # Remove file from all commits
   git filter-branch --force --index-filter \
   "git rm --cached --ignore-unmatch .env" \
   --prune-empty --tag-name-filter cat -- --all
   
   # Force push (WARNING: Rewrites history)
   git push origin --force --all
   ```

### 💡Tips for Safe GitHub Usage

1. **Use `.env.example` as your guide**:
   - Always keep it updated with new variables
   - Never put real values in it
   
2. **Double-check before pushing**:
   ```bash
   git diff HEAD
   ```

3. **Enable GitHub Secret Scanning** (recommended):
   - Go to repository Settings → Security → Secret scanning
   - GitHub will alert you if credentials are detected

4. **Consider making repository private**:
   - Especially during development
   - Can make public later after thorough review

5. **Review public commits regularly**:
   - Check `https://github.com/Nodrun54/polymarket.git`
   - Look for any accidental exposure

---

## ⚠️ Disclaimer

**Financial Risk**: Trading crypto and prediction markets involves significant risk. This bot is provided for educational purposes. Never trade funds you cannot afford to lose. The developers are not responsible for any financial losses incurred.

---

