import time
import logging
from typing import List, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class FMPClient:
    BASE_URL = "https://financialmodelingprep.com/api/v3"

    # Only retry transient status codes.
    RETRYABLE_STATUSES = {408, 409, 425, 429, 500, 502, 503, 504}

    def __init__(self, api_key: str, timeout: int, max_retries: int):
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.Client(timeout=self.timeout)

    def _should_retry_status(self, status_code: int) -> bool:
        return status_code in self.RETRYABLE_STATUSES

    def _get_with_retries(self, url: str) -> List[Dict[str, Any]]:
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.get(url)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                logger.warning(
                    "HTTP error %s for %s, attempt %s",
                    status_code,
                    url,
                    attempt + 1,
                )

                if not self._should_retry_status(status_code):
                    raise

                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)  # exponential backoff
                else:
                    raise
            except httpx.HTTPError as e:
                status_code = getattr(getattr(e, "response", None), "status_code", None)
                if status_code is not None:
                    logger.warning(
                        "HTTP error %s for %s, attempt %s",
                        status_code,
                        url,
                        attempt + 1,
                    )
                    if not self._should_retry_status(status_code):
                        raise
                else:
                    logger.warning(f"HTTP error fetching {url}, attempt {attempt + 1}: {e}")
                    if "403" in str(e):
                        raise

                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
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
