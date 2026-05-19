"""
MOPS HTML Client — fetches and parses HTML tables from TWSE MOPS.
Used for revenue, share pledging, dividends, and disclosure data.
For XBRL financial report downloads use MOPSXBRLClient instead.
"""

import asyncio
import logging
import time
from io import StringIO
from typing import Optional

import httpx
import pandas as pd

try:
    import certifi
except ImportError:
    certifi = None

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30.0
DEFAULT_RATE_LIMIT = 1.0
DEFAULT_MAX_RETRIES = 3


class MOPSHTMLClientError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class MOPSRateLimitError(MOPSHTMLClientError):
    pass


class MOPSDataNotFoundError(MOPSHTMLClientError):
    pass


class MOPSParsingError(MOPSHTMLClientError):
    pass


class MOPSHTMLClient:
    """
    MOPS 公開資訊觀測站 HTML 客戶端

    Fetches HTML table data (monthly revenue, pledging, endorsement, dividends).
    Rate-limits requests to avoid IP bans; handles Big5/UTF-8 encoding.
    """

    MOPS_BASE = "https://mopsov.twse.com.tw"
    MOPS_AJAX_BASE = f"{MOPS_BASE}/mops/web"
    REVENUE_URL_PATTERN = f"{MOPS_BASE}/nas/t21/{{market}}/t21sc03_{{year}}_{{month}}_{{company_type}}.html"

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    def __init__(
        self,
        rate_limit: float = DEFAULT_RATE_LIMIT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: float = DEFAULT_TIMEOUT,
        verify_ssl: bool = True,
    ):
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._last_request_time: float = 0

    async def _rate_limit_wait(self) -> None:
        now = time.time()
        wait_time = self.rate_limit - (now - self._last_request_time)
        if wait_time > 0:
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        self._last_request_time = time.time()

    def _rate_limit_wait_sync(self) -> None:
        now = time.time()
        wait_time = self.rate_limit - (now - self._last_request_time)
        if wait_time > 0:
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            time.sleep(wait_time)
        self._last_request_time = time.time()

    def _get_headers(self, referer: Optional[str] = None) -> dict:
        headers = self.DEFAULT_HEADERS.copy()
        headers["Referer"] = referer or self.MOPS_BASE
        return headers

    def fetch_html_table(
        self,
        endpoint: str,
        params: dict,
        method: str = "POST",
        encoding: str = "utf-8",
    ) -> list[pd.DataFrame]:
        """
        Fetch an MOPS AJAX endpoint and return parsed DataFrames (synchronous version).

        Args:
            endpoint: MOPS endpoint name (e.g., "ajax_t05st11")
            params: Request parameters (form data for POST, query params for GET)
            method: "POST" or "GET"
            encoding: Response encoding ("utf-8" or "big5")
        """
        self._rate_limit_wait_sync()

        url = f"{self.MOPS_AJAX_BASE}/{endpoint}"
        ssl_verified = False

        for attempt in range(self.max_retries):
            try:
                verify_ssl = self.verify_ssl

                # Try with SSL verification first, then fallback to unverified
                if attempt > 0 and self.verify_ssl:
                    verify_ssl = False
                    if not ssl_verified:
                        logger.warning(
                            "SSL verification failed for MOPS; retrying without verification. "
                            "This may be due to MOPS certificate issues. "
                            "Consider updating your SSL certificates with: pip install certifi"
                        )

                with httpx.Client(
                    timeout=self.timeout,
                    follow_redirects=True,
                    verify=verify_ssl,
                ) as client:
                    if method.upper() == "POST":
                        resp = client.post(
                            url, data=params, headers=self._get_headers(url)
                        )
                    else:
                        resp = client.get(
                            url, params=params, headers=self._get_headers(url)
                        )

                    if resp.status_code != 200:
                        raise MOPSHTMLClientError(
                            f"HTTP {resp.status_code}", resp.status_code
                        )

                    resp.encoding = encoding
                    html_content = resp.text

                    if "查無資料" in html_content or "查無符合資料" in html_content:
                        raise MOPSDataNotFoundError("No data found for the query")

                    try:
                        dfs = pd.read_html(StringIO(html_content))
                        logger.info(f"Parsed {len(dfs)} tables from {endpoint}")
                        ssl_verified = True
                        return dfs
                    except ValueError as e:
                        raise MOPSParsingError(f"No tables found in response: {e}")

            except httpx.ConnectError as e:
                if "SSL" in str(e) or "CERTIFICATE" in str(e):
                    logger.debug(
                        f"SSL error attempt {attempt + 1}/{self.max_retries}: {e}"
                    )
                    if attempt < self.max_retries - 1:
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    raise MOPSHTMLClientError(
                        f"SSL verification failed after retries: {e}"
                    )
                raise MOPSHTMLClientError(f"Connection error: {e}")

            except httpx.TimeoutException:
                logger.warning(
                    f"Timeout attempt {attempt + 1}/{self.max_retries} for {endpoint}"
                )
                if attempt == self.max_retries - 1:
                    raise MOPSHTMLClientError("Request timeout after retries")
                time.sleep(1 * (attempt + 1))

            except httpx.HTTPError as e:
                raise MOPSHTMLClientError(f"HTTP error: {e}")

            except (MOPSDataNotFoundError, MOPSParsingError):
                raise

        raise MOPSHTMLClientError(f"Failed to fetch data from {endpoint}")

    async def fetch_html_table_async(
        self,
        endpoint: str,
        params: dict,
        method: str = "POST",
        encoding: str = "utf-8",
    ) -> list[pd.DataFrame]:
        """
        Fetch an MOPS AJAX endpoint and return parsed DataFrames (asynchronous version).

        Args:
            endpoint: MOPS endpoint name (e.g., "ajax_t05st11")
            params: Request parameters (form data for POST, query params for GET)
            method: "POST" or "GET"
            encoding: Response encoding ("utf-8" or "big5")
        """
        await self._rate_limit_wait()

        url = f"{self.MOPS_AJAX_BASE}/{endpoint}"
        ssl_verified = False

        for attempt in range(self.max_retries):
            try:
                verify_ssl = self.verify_ssl

                # Try with SSL verification first, then fallback to unverified
                if attempt > 0 and self.verify_ssl:
                    verify_ssl = False
                    if not ssl_verified:
                        logger.warning(
                            "SSL verification failed for MOPS; retrying without verification. "
                            "This may be due to MOPS certificate issues. "
                            "Consider updating your SSL certificates with: pip install certifi"
                        )

                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    verify=verify_ssl,
                ) as client:
                    if method.upper() == "POST":
                        resp = await client.post(
                            url, data=params, headers=self._get_headers(url)
                        )
                    else:
                        resp = await client.get(
                            url, params=params, headers=self._get_headers(url)
                        )

                    if resp.status_code != 200:
                        raise MOPSHTMLClientError(
                            f"HTTP {resp.status_code}", resp.status_code
                        )

                    resp.encoding = encoding
                    html_content = resp.text

                    if "查無資料" in html_content or "查無符合資料" in html_content:
                        raise MOPSDataNotFoundError("No data found for the query")

                    try:
                        dfs = pd.read_html(StringIO(html_content))
                        logger.info(f"Parsed {len(dfs)} tables from {endpoint}")
                        ssl_verified = True
                        return dfs
                    except ValueError as e:
                        raise MOPSParsingError(f"No tables found in response: {e}")

            except httpx.ConnectError as e:
                if "SSL" in str(e) or "CERTIFICATE" in str(e):
                    logger.debug(
                        f"SSL error attempt {attempt + 1}/{self.max_retries}: {e}"
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    raise MOPSHTMLClientError(
                        f"SSL verification failed after retries: {e}"
                    )
                raise MOPSHTMLClientError(f"Connection error: {e}")

            except httpx.TimeoutException:
                logger.warning(
                    f"Timeout attempt {attempt + 1}/{self.max_retries} for {endpoint}"
                )
                if attempt == self.max_retries - 1:
                    raise MOPSHTMLClientError("Request timeout after retries")
                await asyncio.sleep(1 * (attempt + 1))

            except httpx.HTTPError as e:
                raise MOPSHTMLClientError(f"HTTP error: {e}")

            except (MOPSDataNotFoundError, MOPSParsingError):
                raise

        raise MOPSHTMLClientError(f"Failed to fetch data from {endpoint}")

    def fetch_static_html(
        self,
        url: str,
        encoding: str = "big5",
    ) -> list[pd.DataFrame]:
        """
        Fetch a static MOPS HTML page (e.g., monthly revenue) and return parsed DataFrames (synchronous version).
        """
        self._rate_limit_wait_sync()

        for attempt in range(self.max_retries):
            try:
                verify_ssl = self.verify_ssl

                # Try with SSL verification first, then fallback to unverified
                if attempt > 0 and self.verify_ssl:
                    verify_ssl = False
                    if attempt == 1:
                        logger.warning(
                            "SSL verification failed for MOPS; retrying without verification. "
                            "This may be due to MOPS certificate issues. "
                            "Consider updating your SSL certificates with: pip install certifi"
                        )

                with httpx.Client(
                    timeout=self.timeout,
                    follow_redirects=True,
                    verify=verify_ssl,
                ) as client:
                    resp = client.get(url, headers=self._get_headers())

                    if resp.status_code == 404:
                        raise MOPSDataNotFoundError(f"Page not found: {url}")

                    if resp.status_code != 200:
                        raise MOPSHTMLClientError(
                            f"HTTP {resp.status_code}", resp.status_code
                        )

                    resp.encoding = encoding
                    html_content = resp.text

                    try:
                        dfs = pd.read_html(StringIO(html_content))
                        logger.info(f"Parsed {len(dfs)} tables from static HTML")
                        return dfs
                    except ValueError as e:
                        raise MOPSParsingError(f"No tables found in response: {e}")

            except httpx.ConnectError as e:
                if "SSL" in str(e) or "CERTIFICATE" in str(e):
                    logger.debug(
                        f"SSL error attempt {attempt + 1}/{self.max_retries}: {e}"
                    )
                    if attempt < self.max_retries - 1:
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    raise MOPSHTMLClientError(
                        f"SSL verification failed after retries: {e}"
                    )
                raise MOPSHTMLClientError(f"Connection error: {e}")

            except httpx.TimeoutException:
                logger.warning(f"Timeout attempt {attempt + 1}/{self.max_retries}")
                if attempt == self.max_retries - 1:
                    raise MOPSHTMLClientError("Request timeout after retries")
                time.sleep(1 * (attempt + 1))

            except httpx.HTTPError as e:
                raise MOPSHTMLClientError(f"HTTP error: {e}")

            except (MOPSDataNotFoundError, MOPSParsingError):
                raise

        raise MOPSHTMLClientError(f"Failed to fetch static HTML from {url}")

    async def fetch_static_html_async(
        self,
        url: str,
        encoding: str = "big5",
    ) -> list[pd.DataFrame]:
        """
        Fetch a static MOPS HTML page (e.g., monthly revenue) and return parsed DataFrames (asynchronous version).
        """
        await self._rate_limit_wait()

        for attempt in range(self.max_retries):
            try:
                verify_ssl = self.verify_ssl

                # Try with SSL verification first, then fallback to unverified
                if attempt > 0 and self.verify_ssl:
                    verify_ssl = False
                    if attempt == 1:
                        logger.warning(
                            "SSL verification failed for MOPS; retrying without verification. "
                            "This may be due to MOPS certificate issues. "
                            "Consider updating your SSL certificates with: pip install certifi"
                        )

                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    verify=verify_ssl,
                ) as client:
                    resp = await client.get(url, headers=self._get_headers())

                    if resp.status_code == 404:
                        raise MOPSDataNotFoundError(f"Page not found: {url}")

                    if resp.status_code != 200:
                        raise MOPSHTMLClientError(
                            f"HTTP {resp.status_code}", resp.status_code
                        )

                    resp.encoding = encoding
                    html_content = resp.text

                    try:
                        dfs = pd.read_html(StringIO(html_content))
                        logger.info(f"Parsed {len(dfs)} tables from static HTML")
                        return dfs
                    except ValueError as e:
                        raise MOPSParsingError(f"No tables found in response: {e}")

            except httpx.ConnectError as e:
                if "SSL" in str(e) or "CERTIFICATE" in str(e):
                    logger.debug(
                        f"SSL error attempt {attempt + 1}/{self.max_retries}: {e}"
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    raise MOPSHTMLClientError(
                        f"SSL verification failed after retries: {e}"
                    )
                raise MOPSHTMLClientError(f"Connection error: {e}")

            except httpx.TimeoutException:
                logger.warning(f"Timeout attempt {attempt + 1}/{self.max_retries}")
                if attempt == self.max_retries - 1:
                    raise MOPSHTMLClientError("Request timeout after retries")
                await asyncio.sleep(1 * (attempt + 1))

            except httpx.HTTPError as e:
                raise MOPSHTMLClientError(f"HTTP error: {e}")

            except (MOPSDataNotFoundError, MOPSParsingError):
                raise

        raise MOPSHTMLClientError(f"Failed to fetch static HTML from {url}")
