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

## 💻 Installation by Operating System

Choose your platform for detailed setup instructions:
- [Windows](#windows-installation) (PowerShell/CMD)
- [Linux](#linux-installation) (Ubuntu/Debian/RHEL)
- [macOS](#macos-installation) (Bash/Zsh)
- [VPS/Cloud](#vps-deployment) (Ubuntu Server)

---

### Windows Installation

#### Step 1: Install Python

1. Download Python 3.8+ from [python.org](https://www.python.org/downloads/)
2. **IMPORTANT**: Check "Add Python to PATH" during installation
3. Verify installation:
   ```powershell
   python --version
   # Should show Python 3.8 or higher
   ```

#### Step 2: Clone the Repository

**Using PowerShell** (Recommended):
```powershell
# Navigate to desired directory
cd ~\Desktop

# Clone repository
git clone https://github.com/Nodrun54/polymarket.git
cd polymarket
```

**Using CMD**:
```cmd
cd %USERPROFILE%\Desktop
git clone https://github.com/Nodrun54/polymarket.git
cd polymarket
```

#### Step 3: Create Virtual Environment

**PowerShell**:
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# If you get execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**CMD**:
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

#### Step 4: Install Dependencies

```powershell
# Upgrade pip first
python -m pip install --upgrade pip

# Install required packages
pip install -r requirements.txt
```

#### Step 5: Configure Environment Variables

**Option A: Using `.env` file** (Recommended):
```powershell
# Copy template
Copy-Item .env.example .env

# Edit with notepad
notepad .env
# Fill in your actual credentials and save
```

**Option B: PowerShell session variables**:
```powershell
$env:POLYMARKET_API_KEY="your_actual_api_key"
$env:POLYMARKET_SECRET="your_actual_secret"
$env:POLYMARKET_PASSPHRASE="your_actual_passphrase"
$env:POLYMARKET_PRIVATE_KEY="0xYOUR_ACTUAL_PRIVATE_KEY"
$env:POLYMARKET_FUNDER="0xYOUR_WALLET_ADDRESS"
```

> [!NOTE]
> Session variables only persist until you close PowerShell. Use `.env` file for permanent configuration.

---

### Linux Installation

Tested on Ubuntu 20.04/22.04, Debian 11+, RHEL 8+

#### Step 1: Install Python & Git

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

**RHEL/CentOS/Fedora**:
```bash
sudo dnf install -y python3 python3-pip git
```

#### Step 2: Clone Repository

```bash
# Navigate to home directory
cd ~

# Clone repository
git clone https://github.com/Nodrun54/polymarket.git
cd polymarket
```

#### Step 3: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Your prompt should now show (.venv)
```

#### Step 4: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install packages
pip install -r requirements.txt
```

#### Step 5: Configure Environment Variables

**Option A: Using `.env` file** (Recommended):
```bash
# Copy template
cp .env.example .env

# Edit with your preferred editor
nano .env   # or vim, vi, gedit, etc.
```

**Option B: Bash session variables**:
```bash
export POLYMARKET_API_KEY="your_actual_api_key"
export POLYMARKET_SECRET="your_actual_secret"
export POLYMARKET_PASSPHRASE="your_actual_passphrase"
export POLYMARKET_PRIVATE_KEY="0xYOUR_ACTUAL_PRIVATE_KEY"
export POLYMARKET_FUNDER="0xYOUR_WALLET_ADDRESS"
```

**Option C: Permanent bash configuration**:
```bash
# Add to ~/.bashrc for permanent setup
echo 'export POLYMARKET_API_KEY="your_actual_api_key"' >> ~/.bashrc
echo 'export POLYMARKET_SECRET="your_actual_secret"' >> ~/.bashrc
# ... repeat for other variables

# Reload configuration
source ~/.bashrc
```

---

### macOS Installation

#### Step 1: Install Homebrew & Python

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11

# Verify installation
python3 --version
```

#### Step 2: Clone Repository

```bash
# Navigate to home directory
cd ~

# Clone repository
git clone https://github.com/Nodrun54/polymarket.git
cd polymarket
```

#### Step 3: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate (works for both Bash and Zsh)
source .venv/bin/activate
```

#### Step 4: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install packages
pip install -r requirements.txt
```

#### Step 5: Configure Environment Variables

**Option A: Using `.env` file** (Recommended):
```bash
# Copy template
cp .env.example .env

# Edit with TextEdit or terminal editor
open .env  # Opens in default text editor
# OR
nano .env
```

**Option B: Zsh session variables** (macOS default shell):
```zsh
export POLYMARKET_API_KEY="your_actual_api_key"
export POLYMARKET_SECRET="your_actual_secret"
export POLYMARKET_PASSPHRASE="your_actual_passphrase"
export POLYMARKET_PRIVATE_KEY="0xYOUR_ACTUAL_PRIVATE_KEY"
export POLYMARKET_FUNDER="0xYOUR_WALLET_ADDRESS"
```

**Option C: Permanent Zsh configuration**:
```zsh
# Add to ~/.zshrc
nano ~/.zshrc

# Add these lines:
export POLYMARKET_API_KEY="your_actual_api_key"
export POLYMARKET_SECRET="your_actual_secret"
# ... etc

# Reload configuration
source ~/.zshrc
```

---

### VPS Deployment

Optimized for Ubuntu Server 20.04/22.04 on cloud platforms (AWS, DigitalOcean, Linode, etc.)

#### Step 1: Initial Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv git screen tmux

# Create non-root user (if not exists)
sudo adduser trader
sudo usermod -aG sudo trader

# Switch to non-root user
su - trader
```

#### Step 2: Clone & Setup

```bash
# Clone repository
cd ~
git clone https://github.com/Nodrun54/polymarket.git
cd polymarket

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 3: Configure Environment Variables

```bash
# Create .env file
cp .env.example .env
nano .env
# Fill in your credentials, save with Ctrl+X, Y, Enter
```

#### Step 4: Test the Bot

```bash
# Test in dry-run mode
python main.py --dry-run --coin BTC --tf 15m

# If successful, you'll see the dashboard
# Press Ctrl+C to exit
```

#### Step 5: Run Persistently with Screen/Tmux

**Using Screen**:
```bash
# Start a new screen session
screen -S polymarket-bot

# Run the bot (inside screen)
source .venv/bin/activate
python main.py --coin BTC --tf 15m --paper

# Detach from screen: Press Ctrl+A, then D
# Reattach later: screen -r polymarket-bot
# List sessions: screen -ls
```

**Using Tmux**:
```bash
# Start tmux session
tmux new -s polymarket-bot

# Run the bot (inside tmux)
source .venv/bin/activate
python main.py --coin BTC --tf 15m --paper

# Detach: Press Ctrl+B, then D
# Reattach: tmux attach -t polymarket-bot
# List sessions: tmux ls
```

#### Step 6: Auto-Start on Boot (Optional)

Create a systemd service:

```bash
# Create service file
sudo nano /etc/systemd/system/polymarket-bot.service
```

Add this content (adjust paths):
```ini
[Unit]
Description=Polymarket Trading Bot
After=network.target

[Service]
Type=simple
User=trader
WorkingDirectory=/home/trader/polymarket
Environment="PATH=/home/trader/polymarket/.venv/bin"
ExecStart=/home/trader/polymarket/.venv/bin/python main.py --coin BTC --tf 15m
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable polymarket-bot
sudo systemctl start polymarket-bot

# Check status
sudo systemctl status polymarket-bot

# View logs
sudo journalctl -u polymarket-bot -f
```

#### VPS Security Tips

```bash
# 1. Setup firewall (allow SSH only)
sudo ufw allow OpenSSH
sudo ufw enable

# 2. Disable root login (edit sshd_config)
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
sudo systemctl restart sshd

# 3. Set up SSH keys instead of passwords
# (Generate on your local machine, copy to VPS)

# 4. Keep system updated
sudo apt update && sudo apt upgrade -y
```

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
   git remote add origin https://github.com/YOUR_USERNAME/polymarket-trading-bot.git
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
   - Check `https://github.com/YOUR_USERNAME/YOUR_REPO/commits`
   - Look for any accidental exposure

---

## ⚠️ Disclaimer

**Financial Risk**: Trading crypto and prediction markets involves significant risk. This bot is provided for educational purposes. Never trade funds you cannot afford to lose. The developers are not responsible for any financial losses incurred.

---
