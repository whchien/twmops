"""
MOPS XBRL Client — downloads XBRL/iXBRL financial report files from TWSE MOPS.
For HTML table crawling use MOPSHTMLClient instead.
"""
import asyncio
import io
import logging
import time
import zipfile
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

try:
    import certifi
except ImportError:
    certifi = None

DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 3


class MOPSXBRLClientError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class MOPSXBRLClient:
    """
    MOPS 公開資訊觀測站 XBRL 客戶端

    Downloads iXBRL/ZIP financial filings.
    Year parameters are ROC year (民國年, e.g. 113 = 2024).
    """

    MOPS_BASE = "https://mopsov.twse.com.tw"
    DOWNLOAD_URL = (
        "{base}/server-java/FileDownLoad"
        "?functionName=t164sb01&step=9"
        "&co_id={stock_id}&year={year}&season={quarter}&report_id={report_id}"
    )

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        verify_ssl: bool = True,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl

    def download_xbrl(
        self,
        stock_id: str,
        year: int,
        quarter: int,
        report_type: str = "C",  # C=consolidated, A=standalone
    ) -> bytes:
        """
        Download an iXBRL file from MOPS (synchronous version).

        Args:
            stock_id: Stock ID (e.g., "2330")
            year: ROC year (民國年, e.g. 113)
            quarter: Quarter (1–4)
            report_type: "C" = consolidated (合併), "A" = standalone (個別)

        Returns:
            Raw bytes (either iXBRL HTML or ZIP)
        """
        western_year = year + 1911

        download_url = self.DOWNLOAD_URL.format(
            base=self.MOPS_BASE,
            stock_id=stock_id,
            year=western_year,
            quarter=quarter,
            report_id=report_type,
        )

        logger.info(f"Downloading from MOPS: {stock_id} {year}Q{quarter}")

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
                    resp = client.get(download_url, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Referer": f"{self.MOPS_BASE}/mops/web/t203sb01",
                    })

                    if resp.status_code == 200:
                        content = resp.content

                        if self.is_ixbrl(content):
                            logger.info(f"Downloaded iXBRL ({len(content):,} bytes)")
                            return content

                        if content[:2] == b"PK":
                            logger.info(f"Downloaded ZIP ({len(content):,} bytes)")
                            return content

                        raise MOPSXBRLClientError("MOPS returned invalid content")
                    else:
                        raise MOPSXBRLClientError(f"HTTP {resp.status_code}", resp.status_code)

            except httpx.ConnectError as e:
                if "SSL" in str(e) or "CERTIFICATE" in str(e):
                    logger.debug(f"SSL error attempt {attempt + 1}/{self.max_retries}: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    raise MOPSXBRLClientError(f"SSL verification failed after retries: {e}")
                raise MOPSXBRLClientError(f"Connection error: {e}")

            except httpx.TimeoutException:
                logger.warning(f"Timeout attempt {attempt + 1}/{self.max_retries}")
                if attempt == self.max_retries - 1:
                    raise MOPSXBRLClientError("Download timeout")
                time.sleep(1 * (attempt + 1))

            except httpx.HTTPError as e:
                raise MOPSXBRLClientError(f"HTTP error: {e}")

        raise MOPSXBRLClientError(f"Failed to download XBRL for {stock_id} {year}Q{quarter}")

    async def download_xbrl_async(
        self,
        stock_id: str,
        year: int,
        quarter: int,
        report_type: str = "C",
    ) -> bytes:
        """
        Download an iXBRL file from MOPS (asynchronous version).

        Args:
            stock_id: Stock ID (e.g., "2330")
            year: ROC year (民國年, e.g. 113)
            quarter: Quarter (1–4)
            report_type: "C" = consolidated (合併), "A" = standalone (個別)

        Returns:
            Raw bytes (either iXBRL HTML or ZIP)
        """
        western_year = year + 1911

        download_url = self.DOWNLOAD_URL.format(
            base=self.MOPS_BASE,
            stock_id=stock_id,
            year=western_year,
            quarter=quarter,
            report_id=report_type,
        )

        logger.info(f"Downloading from MOPS: {stock_id} {year}Q{quarter}")

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
                    resp = await client.get(download_url, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Referer": f"{self.MOPS_BASE}/mops/web/t203sb01",
                    })

                    if resp.status_code == 200:
                        content = resp.content

                        if self.is_ixbrl(content):
                            logger.info(f"Downloaded iXBRL ({len(content):,} bytes)")
                            return content

                        if content[:2] == b"PK":
                            logger.info(f"Downloaded ZIP ({len(content):,} bytes)")
                            return content

                        raise MOPSXBRLClientError("MOPS returned invalid content")
                    else:
                        raise MOPSXBRLClientError(f"HTTP {resp.status_code}", resp.status_code)

            except httpx.ConnectError as e:
                if "SSL" in str(e) or "CERTIFICATE" in str(e):
                    logger.debug(f"SSL error attempt {attempt + 1}/{self.max_retries}: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    raise MOPSXBRLClientError(f"SSL verification failed after retries: {e}")
                raise MOPSXBRLClientError(f"Connection error: {e}")

            except httpx.TimeoutException:
                logger.warning(f"Timeout attempt {attempt + 1}/{self.max_retries}")
                if attempt == self.max_retries - 1:
                    raise MOPSXBRLClientError("Download timeout")
                await asyncio.sleep(1 * (attempt + 1))

            except httpx.HTTPError as e:
                raise MOPSXBRLClientError(f"HTTP error: {e}")

        raise MOPSXBRLClientError(f"Failed to download XBRL for {stock_id} {year}Q{quarter}")

    def extract_zip(self, zip_content: bytes) -> dict[str, bytes]:
        """Unzip an XBRL ZIP archive into {filename: bytes}."""
        files = {}
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            for name in zf.namelist():
                files[name] = zf.read(name)
        return files

    def is_ixbrl(self, content: bytes) -> bool:
        """Check whether content is iXBRL format."""
        return b"ix:nonFraction" in content or b"ix:nonNumeric" in content
