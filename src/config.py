import os
import json
from pathlib import Path
from typing import List

class Config:
    def __init__(self):
        self.fmp_api_key = os.getenv("FMP_API_KEY", "")
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.request_timeout_seconds = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))

    def load_watchlist(self) -> List[str]:
        watchlist_path = Path("config/watchlist.json")
        if not watchlist_path.exists():
            return []
        with open(watchlist_path, "r") as f:
            data = json.load(f)
        # Normalize: uppercase, remove duplicates, ignore empty
        symbols = [s.upper().strip() for s in data if s and isinstance(s, str)]
        return list(set(symbols))