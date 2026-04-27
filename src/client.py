import time
import logging
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class FMPClient:
    BASE_URL = "https://financialmodelingprep.com/api/v3"

    # Only retry transient status codes.
    RETRYABLE_STATUSES = {408, 409, 425, 429, 500, 502, 503, 504}

    def __init__(self, api_key: str, timeout: int, max_retries: int):
        self.api_key = api_key
        self.timeout = timeout
        # Number of *extra* attempts after the initial request. The constructor
        # arg name (and the MAX_RETRIES env var) keep their historical meaning
        # for backward compat — total attempts per call = extra_retries + 1.
        # E.g. MAX_RETRIES=3 → 4 total attempts.
        self.extra_retries = max_retries
        self.client = httpx.Client(timeout=self.timeout)

    def __enter__(self) -> "FMPClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self.client.close()

    def _should_retry_status(self, status_code: int) -> bool:
        return status_code in self.RETRYABLE_STATUSES

    def _get_with_retries(self, url: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        for attempt in range(self.extra_retries + 1):
            try:
                response = self.client.get(url, params=params)
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

                if attempt < self.extra_retries:
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
                    # Non-status httpx.HTTPError (transport, decode, etc.).
                    # Real 403s carry a status code and are handled in the
                    # branch above — string-matching the message for "403"
                    # produced false positives (e.g., port 4030 in a connect
                    # error), so we don't try to re-detect them here.
                    logger.warning(f"HTTP error fetching {url}, attempt {attempt + 1}: {e}")

                if attempt < self.extra_retries:
                    time.sleep(2 ** attempt)
                else:
                    raise
            except Exception as e:
                logger.warning(f"Error fetching {url}, attempt {attempt + 1}: {e}")
                if attempt < self.extra_retries:
                    time.sleep(2 ** attempt)
                else:
                    raise
        # Unreachable: every iteration either returns or raises. Config now
        # validates max_retries >= 0 so the loop always runs at least once.
        raise RuntimeError("FMPClient._get_with_retries: unreachable")

    def _coerce_records(self, data: Any, endpoint: str, symbol: str) -> List[Dict[str, Any]]:
        """FMP usually returns a list, but on bad credentials / quota errors it
        returns HTTP 200 with a JSON dict body like {"Error Message": "..."}.
        Treat anything other than a list as a non-retryable failure for this
        symbol/chamber: log the error message (without the API key) and return
        an empty list so the caller skips this fetch but the run continues."""
        if isinstance(data, list):
            return data
        msg = ""
        if isinstance(data, dict):
            msg = data.get("Error Message") or data.get("error") or "(non-list response)"
        logger.error(
            "FMP %s returned non-list response for %s: %s",
            endpoint, symbol, msg,
        )
        return []

    def get_senate_trades(self, symbol: str) -> List[Dict[str, Any]]:
        logger.info(f"Fetching senate trades for {symbol}")
        time.sleep(1)  # conservative rate limiting
        data = self._get_with_retries(
            f"{self.BASE_URL}/senate-trades",
            params={"symbol": symbol, "apikey": self.api_key},
        )
        return self._coerce_records(data, "senate-trades", symbol)

    def get_house_trades(self, symbol: str) -> List[Dict[str, Any]]:
        logger.info(f"Fetching house trades for {symbol}")
        time.sleep(1)  # conservative rate limiting
        data = self._get_with_retries(
            f"{self.BASE_URL}/house-trades",
            params={"symbol": symbol, "apikey": self.api_key},
        )
        return self._coerce_records(data, "house-trades", symbol)
