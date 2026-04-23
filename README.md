# Congressional Trade Watcher

A small, reliable system that watches for newly published U.S. congressional trade disclosures involving a user-supplied watchlist of stock symbols and sends alerts once per newly detected disclosure.

## Overview

This tool monitors congressional trade disclosures using Financial Modeling Prep's free API endpoints. It fetches Senate and House trade data daily, normalizes the records, deduplicates based on fingerprints, and sends Discord alerts for new disclosures.

**Important Notes:**
- Alerts are delayed by nature: Congressional disclosures are filed after trades under the STOCK Act.
- This is informational monitoring, not trading advice.
- Upstream data is updated daily by FMP.

## Setup

1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your values.
4. Add symbols to `config/watchlist.json` (e.g., `["NVDA", "PLTR"]`).
5. Run backfill: `python -m src.main backfill --days 30`
6. Schedule daily runs or run manually.

## Configuration

### Environment Variables (.env)

- `FMP_API_KEY`: Your Financial Modeling Prep API key (get from https://financialmodelingprep.com/)
- `DISCORD_WEBHOOK_URL`: Discord webhook URL for alerts
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `REQUEST_TIMEOUT_SECONDS`: HTTP timeout
- `MAX_RETRIES`: Max retries for failed requests

For GitHub Actions, do not commit your `.env` file. Instead, add repository secrets in GitHub:

1. Go to your repository on GitHub.
2. Click `Settings`.
3. Select `Secrets and variables` > `Actions`.
4. Click `New repository secret`.
5. Add the secret name `FMP_API_KEY` and paste its value.
6. Add the secret name `DISCORD_WEBHOOK_URL` and paste its value.
7. Save each secret.

These secrets are encrypted and only available during the workflow run.

### Watchlist

Edit `config/watchlist.json` with your symbols:

```json
["ARM", "GEV", "NVDA", "TSM", "TPL", "STX", "ANET", "VRT", "ETN", "EQIX", "NVT", "AVGO", "APD", "LITE", "ASML"]
```

Symbols are normalized to uppercase, duplicates removed.

## Usage

### Daily Scan
`python -m src.main run`

Fetches data, checks for new disclosures, sends alerts.

### Test Alert
`python -m src.main test-alert`

Sends a sample alert to verify Discord setup.

### Backfill
`python -m src.main backfill --days 30`

Populates seen hashes without sending alerts. Run before first production use.

## Scheduling

Use cron for daily runs. Example (9 AM daily):

```
0 9 * * * cd /path/to/congress-trade-watcher && python -m src.main run
```

See `src/scheduler_notes.md` for details.

### GitHub Actions Scheduled Runs

If you run this project on GitHub Actions, the included workflow uses:

- `on.schedule: '17 13 * * *'` (UTC daily)
- `workflow_dispatch` for manual runs

This offset from minute `00` is intentional to reduce the chance of missed schedule starts during high-load top-of-hour windows.

## Data Storage

- `data/seen_hashes.json`: Fingerprints of seen records
- `data/last_run.json`: Last run metadata
- `logs/app.log`: Application logs

## Troubleshooting

- Check logs in `logs/app.log`
- Ensure FMP API key is valid
- Verify Discord webhook URL
- If no alerts, check watchlist and run backfill

## Dependencies

- **httpx**: Modern HTTP client for API requests
- **python-dotenv**: Environment variable management from .env files
- **Standard library**: json, hashlib, logging, pathlib, datetime, argparse

For full details, see [REQUIREMENTS.md](REQUIREMENTS.md).

## Documentation

Full documentation is organized as follows:

- [REQUIREMENTS.md](REQUIREMENTS.md): Dependencies and installation details
- [INSTALL.md](INSTALL.md): Step-by-step installation guide
- [User Manual](docs/MANUAL.md): Detailed setup and usage instructions
- [Architectural Decisions](docs/DECISIONS.md): Key design choices and rationale
- [Future Plans](docs/PLANS.md): Roadmap and planned features
- [CONTRIBUTING.md](CONTRIBUTING.md): Guidelines for contributors
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md): Community standards
- [CHANGELOG.md](CHANGELOG.md): Project version history
- [AUTHORS.md](AUTHORS.md): Project contributors
