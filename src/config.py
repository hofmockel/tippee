import os
import json
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Resolve watchlist path relative to the project root (one level above src/),
# so the CLI works no matter what CWD it was launched from.
_WATCHLIST_PATH = Path(__file__).resolve().parent.parent / "config" / "watchlist.json"

class Config:
    def __init__(self):
        self.fmp_api_key = os.getenv("FMP_API_KEY", "")
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.request_timeout_seconds = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.send_disclosure_alerts = os.getenv("SEND_DISCLOSURE_ALERTS", "true").lower() in ("1", "true", "yes")
        self.send_confirmation_alert = os.getenv("SEND_CONFIRMATION_ALERT", "false").lower() in ("1", "true", "yes")
        self.confirmation_message = os.getenv(
            "CONFIRMATION_MESSAGE",
            "Congressional trade watcher run complete. Fetched {total_fetched} record(s). Detected {new_records} new disclosure(s)."
        )

    def load_watchlist(self) -> List[str]:
        if not _WATCHLIST_PATH.exists():
            return []
        with open(_WATCHLIST_PATH, "r") as f:
            data = json.load(f)
        # Normalize: uppercase, strip, drop empties, dedupe while preserving order.
        symbols = [s.upper().strip() for s in data if s and isinstance(s, str)]
        return list(dict.fromkeys(symbols))