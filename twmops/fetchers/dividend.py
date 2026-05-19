"""
DividendFetcher — fetches dividend distribution data from MOPS.
MOPS AJAX endpoint: ajax_t05st09_2 (supports quarterly dividends, e.g. TSMC)
"""

import logging
import re
from typing import Optional, List

from twmops.models.dividend import DividendRecord, DividendSummary, DividendResponse
from twmops.utils.numerics import parse_financial_value
from twmops.clients.html_client import (
    MOPSHTMLClient,
    MOPSHTMLClientError,
    MOPSDataNotFoundError,
)

logger = logging.getLogger(__name__)


class DividendFetcherError(Exception):
    pass


class DividendFetcher:
    """
    Fetch dividend distribution records from MOPS.

    Usage:
        fetcher = DividendFetcher()
        resp = await fetcher.get_dividends("2330", year_start=110, year_end=113)
        summary = await fetcher.get_annual_summary("2330", year=113)
    """

    AJAX_ENDPOINT = "ajax_t05st09_2"

    def __init__(self, html_client: Optional[MOPSHTMLClient] = None):
        self.client = html_client or MOPSHTMLClient()

    def _get_dividend_params(
        self, stock_id: str, year_start: int, year_end: int, query_type: int
    ) -> dict:
        return {
            "encodeURIComponent": 1,
            "step": 1,
            "firstin": 1,
            "off": 1,
            "isnew": "false",
            "co_id": stock_id,
            "date1": year_start,
            "date2": year_end,
            "qryType": str(query_type),
        }

    def _parse_dividend_response(
        self, dfs: list, stock_id: str, year_start: int, year_end: int
    ) -> DividendResponse:
        company_name = self._extract_company_name(dfs, stock_id)
        records = self._parse_dividend_records(dfs, stock_id, company_name)
        logger.info(f"Parsed {len(records)} dividend records for {stock_id}")
        return DividendResponse(
            stock_id=stock_id,
            company_name=company_name,
            year_start=year_start,
            year_end=year_end,
            count=len(records),
            records=records,
        )

    def get_dividends(
        self,
        stock_id: str,
        year_start: int,
        year_end: Optional[int] = None,
        query_type: int = 2,
    ) -> DividendResponse:
        """
        Fetch dividend records for a date range (synchronous version).

        Args:
            stock_id: Stock ID (e.g., "2330")
            year_start: Start ROC year (民國年)
            year_end: End ROC year (defaults to year_start)
            query_type: 1 = board resolution year, 2 = dividend period year
        """
        if year_end is None:
            year_end = year_start

        params = self._get_dividend_params(stock_id, year_start, year_end, query_type)
        logger.info(f"Fetching dividend data: {stock_id} {year_start}-{year_end}")

        try:
            dfs = self.client.fetch_html_table(
                self.AJAX_ENDPOINT, params, method="POST", encoding="utf-8"
            )
        except MOPSDataNotFoundError:
            raise DividendFetcherError(f"No dividend data for {stock_id}")
        except MOPSHTMLClientError as e:
            raise DividendFetcherError(f"Failed to fetch dividend: {e.message}")

        return self._parse_dividend_response(dfs, stock_id, year_start, year_end)

    async def get_dividends_async(
        self,
        stock_id: str,
        year_start: int,
        year_end: Optional[int] = None,
        query_type: int = 2,
    ) -> DividendResponse:
        """
        Fetch dividend records for a date range (asynchronous version).

        Args:
            stock_id: Stock ID (e.g., "2330")
            year_start: Start ROC year (民國年)
            year_end: End ROC year (defaults to year_start)
            query_type: 1 = board resolution year, 2 = dividend period year
        """
        if year_end is None:
            year_end = year_start

        params = self._get_dividend_params(stock_id, year_start, year_end, query_type)
        logger.info(f"Fetching dividend data: {stock_id} {year_start}-{year_end}")

        try:
            dfs = await self.client.fetch_html_table_async(
                self.AJAX_ENDPOINT, params, method="POST", encoding="utf-8"
            )
        except MOPSDataNotFoundError:
            raise DividendFetcherError(f"No dividend data for {stock_id}")
        except MOPSHTMLClientError as e:
            raise DividendFetcherError(f"Failed to fetch dividend: {e.message}")

        return self._parse_dividend_response(dfs, stock_id, year_start, year_end)

    def get_annual_summary(self, stock_id: str, year: int) -> DividendSummary:
        """Fetch all dividends for a year and return a rolled-up summary (synchronous version)."""
        response = self.get_dividends(stock_id, year, year)

        total_cash = sum(r.cash_dividend or 0 for r in response.records)
        total_stock = sum(r.stock_dividend or 0 for r in response.records)

        return DividendSummary(
            stock_id=stock_id,
            company_name=response.company_name,
            year=year,
            total_cash_dividend=round(total_cash, 2),
            total_stock_dividend=round(total_stock, 2),
            total_dividend=round(total_cash + total_stock, 2),
            quarterly_dividends=response.records,
        )

    async def get_annual_summary_async(
        self, stock_id: str, year: int
    ) -> DividendSummary:
        """Fetch all dividends for a year and return a rolled-up summary (asynchronous version)."""
        response = await self.get_dividends_async(stock_id, year, year)

        total_cash = sum(r.cash_dividend or 0 for r in response.records)
        total_stock = sum(r.stock_dividend or 0 for r in response.records)

        return DividendSummary(
            stock_id=stock_id,
            company_name=response.company_name,
            year=year,
            total_cash_dividend=round(total_cash, 2),
            total_stock_dividend=round(total_stock, 2),
            total_dividend=round(total_cash + total_stock, 2),
            quarterly_dividends=response.records,
        )

    def _extract_company_name(self, dfs: list, stock_id: str) -> str:
        for df in dfs:
            if df.shape[0] == 0:
                continue
            val = str(df.iloc[0, 0]) if df.shape[1] > 0 else ""
            if stock_id in val:
                return val.replace(stock_id, "").strip()
        return ""

    def _parse_dividend_records(
        self, dfs: list, stock_id: str, company_name: str
    ) -> List[DividendRecord]:
        records = []
        failure_count = 0

        for df in dfs:
            if df.shape[1] < 3 or df.shape[0] < 2:
                continue

            df_str = df.to_string()
            if "股利所屬期間" not in df_str and "現金股利" not in df_str:
                continue

            df.columns = range(len(df.columns))

            for idx, row in df.iterrows():
                try:
                    first_col = str(row[0]).strip()
                    if "股利" in first_col or "期間" in first_col or first_col == "":
                        continue

                    year = self._extract_year(str(row[1]) if len(row) > 1 else "")
                    if year is None:
                        continue

                    period_str = str(row[1]) if len(row) > 1 else ""
                    quarter = self._extract_quarter(period_str)

                    def _p_float(val):
                        d = parse_financial_value(val)
                        return float(d) if d is not None else None

                    cash_dividend = _p_float(row[6]) if len(row) > 6 else None
                    stock_dividend = _p_float(row[7]) if len(row) > 7 else None

                    board_date = str(row[2]).strip() if len(row) > 2 else None
                    if board_date in ["nan", "", "-"]:
                        board_date = None

                    records.append(
                        DividendRecord(
                            stock_id=stock_id,
                            company_name=company_name,
                            year=year,
                            quarter=quarter,
                            period_start=None,
                            period_end=None,
                            board_resolution_date=board_date,
                            cash_dividend=cash_dividend,
                            stock_dividend=stock_dividend,
                            total_dividend=(cash_dividend or 0) + (stock_dividend or 0),
                        )
                    )

                except Exception as e:
                    failure_count += 1
                    logger.debug(f"Failed to parse dividend row: {e}")
                    continue

        if failure_count > 0:
            logger.warning(
                f"Encountered {failure_count} errors parsing dividend records for {stock_id}"
            )

        return records

    def _extract_year(self, text: str) -> Optional[int]:
        match = re.search(r"(\d+)年", text)
        return int(match.group(1)) if match else None

    def _extract_quarter(self, text: str) -> Optional[int]:
        if "01/01" in text or "03/31" in text:
            return 1
        elif "04/01" in text or "06/30" in text:
            return 2
        elif "07/01" in text or "09/30" in text:
            return 3
        elif "10/01" in text or "12/31" in text:
            return 4
        return None
