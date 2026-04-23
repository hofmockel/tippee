# User Manual

This manual provides detailed instructions for setting up and using the Congressional Trade Watcher.

## Installation

### Prerequisites
- Python 3.11 or higher
- Git
- Internet connection for API access

### Setup Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/hofmockel/tippee.git
   cd tippee
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   
   This installs:
   - **httpx**: HTTP client for API requests
   - **python-dotenv**: Loads environment variables from .env file

4. Copy environment file:
   ```bash
   cp .env.example .env
   ```

5. Edit `.env` with your API keys (see Configuration section).
   
   The application automatically loads environment variables from the `.env` file using python-dotenv.

## Configuration

### Environment Variables
Edit the `.env` file with the following values:

- `FMP_API_KEY`: Get from https://financialmodelingprep.com/developer/docs (free plan available)
- `DISCORD_WEBHOOK_URL`: Create a webhook in your Discord server settings
- `LOG_LEVEL`: INFO (default), DEBUG for verbose logging
- `REQUEST_TIMEOUT_SECONDS`: 20 (default)
- `MAX_RETRIES`: 3 (default)

### Watchlist
Edit `config/watchlist.json` to add stock symbols:

```json
["ARM", "GEV", "NVDA", "TSM", "TPL", "STX", "ANET", "VRT", "ETN", "EQIX", "NVT", "AVGO", "APD", "LITE", "ASML"]
```

Symbols are automatically normalized to uppercase.

## Usage

### Commands

#### Daily Scan
Run the main monitoring process:
```bash
python -m src.main run
```

This fetches data for all watchlist symbols and sends alerts for new disclosures.

#### Test Alert
Verify your Discord setup:
```bash
python -m src.main test-alert
```

Sends a sample alert without fetching data.

#### Backfill
Initialize the system with existing data:
```bash
python -m src.main backfill --days 30
```

Fetches current data and marks all as seen. Run this before first production use.

### Scheduling
Set up daily runs with cron:

```bash
# Edit crontab
crontab -e

# Add line for 9 AM daily run
0 9 * * * cd /path/to/tippee && python -m src.main run
```

Replace `/path/to/tippee` with your actual path.

## Output and Logs

### Console Output
The tool logs to both console and file. Check `logs/app.log` for detailed logs.

### Data Files
- `data/seen_hashes.json`: Stores fingerprints of processed disclosures
- `data/last_run.json`: Metadata from the last run

### Alerts
New disclosures trigger:
- Console log message
- Discord webhook message with details

## Troubleshooting

### No Alerts
- Check `logs/app.log` for errors
- Verify FMP API key is valid
- Ensure watchlist has symbols
- Run backfill if it's the first time

### API Errors
- Check internet connection
- Verify API key hasn't expired
- Look for rate limiting messages

### Discord Not Working
- Test webhook URL manually
- Check Discord server permissions
- Use test-alert command to verify

### Permission Errors
- Ensure write access to data/ and logs/ directories
- Check file permissions

## Data Source Notes

- Disclosures are delayed by STOCK Act requirements
- FMP updates data daily
- Historical data limited to recent years
- Not real-time trade tracking

## Security

- Keep `.env` file secure
- Don't commit API keys to version control
- Use strong, unique API keys
- Regularly rotate keys if needed

## Support

For issues:
1. Check this manual
2. Review logs
3. Open a GitHub issue with log excerpts