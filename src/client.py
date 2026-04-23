import time
import logging
from typing import List, Dict, Any
import httpx

logger = logging.getLogger(__name__)

class FMPClient:
    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: str, timeout: int, max_retries: int):
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.Client(timeout=self.timeout)

    def _get_with_retries(self, url: str) -> List[Dict[str, Any]]:
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.get(url)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error {e.response.status_code} for {url}, attempt {attempt + 1}")
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)  # exponential backoff
                else:
                    raise
            except Exception as e:
                logger.warning(f"Error fetching {url}, attempt {attempt + 1}: {e}")
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                else:
                    raise
        return []

    def get_senate_trades(self, symbol: str) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}/senate-trades?symbol={symbol}&apikey={self.api_key}"
        logger.info(f"Fetching senate trades for {symbol}")
        time.sleep(1)  # conservative rate limiting
        return self._get_with_retries(url)

    def get_house_trades(self, symbol: str) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}/house-trades?symbol={symbol}&apikey={self.api_key}"
        logger.info(f"Fetching house trades for {symbol}")
        time.sleep(1)  # conservative rate limiting
        return self._get_with_retries(url)