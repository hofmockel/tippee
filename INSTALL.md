# Installation Guide

This guide provides step-by-step instructions for installing the Congressional Trade Watcher.

## Prerequisites

Before installing, ensure you have:

- **Python 3.11 or higher** - Download from [python.org](https://python.org)
- **Git** - For cloning the repository
- **Internet connection** - For API access and package installation

### Checking Python Version
```bash
python --version
# Should show Python 3.11.x or higher
```

## Quick Install

### 1. Clone the Repository
```bash
git clone https://github.com/hofmockel/tippee.git
cd tippee
```

### 2. Create Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

This installs:
- **httpx** - Modern HTTP client library for API requests
- **python-dotenv** - Environment variable management from .env files

For details on all dependencies, see [REQUIREMENTS.md](REQUIREMENTS.md).

### 4. Configure Environment
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys (see Configuration section below)
```

### 5. Configure Watchlist
Edit `config/watchlist.json` to add your stock symbols:
```json
["ARM", "GEV", "NVDA", "TSM", "TPL", "STX", "ANET", "VRT", "ETN", "EQIX", "NVT", "AVGO", "APD", "LITE", "ASML"]
```

### 6. Test Installation
```bash
# Test alert to verify Discord setup
python -m src.main test-alert

# Run backfill to initialize data
python -m src.main backfill
```

## Configuration

### Required API Keys

#### Financial Modeling Prep API Key
1. Visit [Financial Modeling Prep](https://financialmodelingprep.com/)
2. Sign up for a free account
3. Get your API key from the dashboard
4. Add to `.env`: `FMP_API_KEY=your_key_here`

#### Discord Webhook (Optional but Recommended)
1. Go to your Discord server settings
2. Navigate to Integrations > Webhooks
3. Create a new webhook for the channel you want alerts in
4. Copy the webhook URL
5. Add to `.env`: `DISCORD_WEBHOOK_URL=your_webhook_url`

### Environment Variables
Edit the `.env` file:
```bash
FMP_API_KEY=your_fmp_key
DISCORD_WEBHOOK_URL=your_discord_webhook
LOG_LEVEL=INFO
REQUEST_TIMEOUT_SECONDS=20
MAX_RETRIES=3
SEND_CONFIRMATION_ALERT=false
CONFIRMATION_MESSAGE=Congressional trade watcher run complete. Fetched {total_fetched} record(s). Detected {new_records} new disclosure(s).
```

By default, the watcher only sends alerts when it detects new disclosures. To receive a heartbeat message even when no new disclosures are found, set `SEND_CONFIRMATION_ALERT=true`.

## Alternative Installation Methods

### Using pip (if packaged)
```bash
# Not yet available - install from source as above
```

### Docker Installation (Future)
```bash
# Docker support planned for v2.0
```

## Troubleshooting Installation

### Python Version Issues
If you have multiple Python versions:
```bash
# Use specific Python version
python3.11 -m venv venv
source venv/bin/activate
python --version  # Should be 3.11+
```

### Permission Errors
On Linux/macOS, ensure you have write permissions in the installation directory.

### Virtual Environment Issues
If virtual environment activation fails:
```bash
# Try alternative activation
. venv/bin/activate
# or
source venv/bin/activate.fish  # for fish shell
```

### Dependency Installation Fails
```bash
# Upgrade pip first
pip install --upgrade pip
# Then install requirements
pip install -r requirements.txt
```

## Next Steps

After installation:
1. Run backfill: `python -m src.main backfill`
2. Test daily run: `python -m src.main run`
3. Set up cron scheduling (see README.md)

For detailed usage instructions, see the [User Manual](docs/MANUAL.md).