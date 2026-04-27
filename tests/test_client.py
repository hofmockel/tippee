import unittest
from unittest.mock import Mock, patch

import httpx

from src.client import FMPClient


class TestFMPClientRetries(unittest.TestCase):
    def setUp(self):
        self.client = FMPClient(api_key="test", timeout=5, max_retries=3)

    def _http_status_error(self, status_code: int, url: str) -> httpx.HTTPStatusError:
        request = httpx.Request("GET", url)
        response = httpx.Response(status_code, request=request)
        return httpx.HTTPStatusError(
            message=f"Status {status_code}",
            request=request,
            response=response,
        )

    @patch("src.client.time.sleep", return_value=None)
    def test_does_not_retry_on_403(self, _sleep_mock):
        url = "https://example.com/test"
        self.client.client.get = Mock(side_effect=self._http_status_error(403, url))

        with self.assertRaises(httpx.HTTPStatusError):
            self.client._get_with_retries(url)

        self.assertEqual(self.client.client.get.call_count, 1)

    @patch("src.client.time.sleep", return_value=None)
    def test_retries_on_429(self, _sleep_mock):
        url = "https://example.com/test"
        err = self._http_status_error(429, url)
        good_response = Mock()
        good_response.raise_for_status = Mock(return_value=None)
        good_response.json = Mock(return_value=[])

        self.client.client.get = Mock(side_effect=[err, err, good_response])

        result = self.client._get_with_retries(url)

        self.assertEqual(result, [])
        self.assertEqual(self.client.client.get.call_count, 3)

    @patch("src.client.time.sleep", return_value=None)
    def test_does_not_retry_on_http_error_message_with_403(self, _sleep_mock):
        url = "https://example.com/test"
        err = httpx.HTTPError("403 Forbidden")
        self.client.client.get = Mock(side_effect=err)

        with self.assertRaises(httpx.HTTPError):
            self.client._get_with_retries(url)

        self.assertEqual(self.client.client.get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
