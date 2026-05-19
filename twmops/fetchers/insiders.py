"""
InsidersFetcher — fetches director/supervisor share pledging data from MOPS.
MOPS AJAX endpoint: ajax_stapap1
"""
import logging
from typing import Optional, List

from pydantic import BaseModel

from twmops.clients.html_client import (
    MOPSHTMLClient,
    MOPSHTMLClientError,
    MOPSDataNotFoundError,
)

logger = logging.getLogger(__name__)


class SharePledging(BaseModel):
    """Individual director/supervisor share pledging record."""
    stock_id: str
    company_name: str
    year: int
    month: int
    title: str
    relationship: str
    name: str
    shares_at_election: Optional[int] = None
    current_shares: Optional[int] = None
    pledged_shares: Optional[int] = None
    pledge_ratio: Optional[float] = None


class PledgingSummary(BaseModel):
    """Aggregated pledging summary for the company."""
    stock_id: str
    company_name: str
    year: int
    month: int
    non_independent_director_shares: Optional[int] = None
    non_independent_director_pledged: Optional[int] = None
    non_independent_director_ratio: Optional[float] = None
    independent_director_shares: Optional[int] = None
    independent_director_pledged: Optional[int] = None
    independent_director_ratio: Optional[float] = None
    total_shares: Optional[int] = None
    total_pledged: Optional[int] = None
    total_pledge_ratio: Optional[float] = None


class PledgingResponse(BaseModel):
    stock_id: str
    company_name: str
    year: int
    month: int
    summary: Optional[PledgingSummary] = None
    details: List[SharePledging] = []


class InsidersFetcherError(Exception):
    pass


class InsidersFetcher:
    """
    Fetch director/supervisor share pledging data from MOPS.

    Usage:
        fetcher = InsidersFetcher()
        data = await fetcher.get_share_pledging("2330", year=113, month=3)
    """

    AJAX_ENDPOINT = "ajax_stapap1"

    def __init__(self, html_client: Optional[MOPSHTMLClient] = None):
        self.client = html_client or MOPSHTMLClient()

    def _get_pledging_params(self, stock_id: str, year: int, month: int, market: str) -> dict:
        return {
            "encodeURIComponent": 1,
            "step": 1,
            "firstin": 1,
            "off": 1,
            "TYPEK": market,
            "year": year,
            "month": str(month).zfill(2),
            "co_id": stock_id,
        }

    def _parse_pledging_response(
        self,
        dfs: list,
        stock_id: str,
        year: int,
        month: int,
    ) -> PledgingResponse:
        company_name = self._extract_company_name(dfs, stock_id)
        details = self._parse_pledging_details(dfs, stock_id, company_name, year, month)
        summary = self._parse_pledging_summary(dfs, stock_id, company_name, year, month)
        logger.info(f"Parsed {len(details)} pledging records for {stock_id}")
        return PledgingResponse(
            stock_id=stock_id,
            company_name=company_name,
            year=year,
            month=month,
            summary=summary,
            details=details,
        )

    def get_share_pledging(
        self,
        stock_id: str,
        year: int,
        month: int,
        market: str = "sii",
    ) -> PledgingResponse:
        """
        Fetch share pledging data for a company (synchronous version).

        Args:
            stock_id: Stock ID (e.g., "2330")
            year: ROC year (民國年)
            month: Month (1–12)
            market: "sii" or "otc"
        """
        params = self._get_pledging_params(stock_id, year, month, market)
        logger.info(f"Fetching pledging data: {stock_id} {year}/{month}")

        try:
            dfs = self.client.fetch_html_table(
                self.AJAX_ENDPOINT, params, method="POST", encoding="utf-8"
            )
        except MOPSDataNotFoundError:
            raise InsidersFetcherError(f"No pledging data for {stock_id}")
        except MOPSHTMLClientError as e:
            raise InsidersFetcherError(f"Failed to fetch pledging: {e.message}")

        return self._parse_pledging_response(dfs, stock_id, year, month)

    async def get_share_pledging_async(
        self,
        stock_id: str,
        year: int,
        month: int,
        market: str = "sii",
    ) -> PledgingResponse:
        """
        Fetch share pledging data for a company (asynchronous version).

        Args:
            stock_id: Stock ID (e.g., "2330")
            year: ROC year (民國年)
            month: Month (1–12)
            market: "sii" or "otc"
        """
        params = self._get_pledging_params(stock_id, year, month, market)
        logger.info(f"Fetching pledging data: {stock_id} {year}/{month}")

        try:
            dfs = await self.client.fetch_html_table_async(
                self.AJAX_ENDPOINT, params, method="POST", encoding="utf-8"
            )
        except MOPSDataNotFoundError:
            raise InsidersFetcherError(f"No pledging data for {stock_id}")
        except MOPSHTMLClientError as e:
            raise InsidersFetcherError(f"Failed to fetch pledging: {e.message}")

        return self._parse_pledging_response(dfs, stock_id, year, month)

    def _extract_company_name(self, dfs: list, stock_id: str) -> str:
        if dfs:
            first_table = dfs[0]
            if len(first_table) > 0:
                val = str(first_table.iloc[0, 0])
                if val.startswith(stock_id):
                    return val[len(stock_id):]
        return ""

    def _parse_pledging_details(
        self,
        dfs: list,
        stock_id: str,
        company_name: str,
        year: int,
        month: int,
    ) -> List[SharePledging]:
        details = []

        for df in dfs:
            if df.shape[1] < 5:
                continue

            first_col = str(df.iloc[0, 0]) if len(df) > 0 else ""
            if "職稱" not in first_col and df.shape[0] < 3:
                continue

            df.columns = range(len(df.columns))

            for idx, row in df.iterrows():
                try:
                    title = str(row[0]).strip()
                    if title == "職稱" or "持股" in title:
                        continue

                    relationship = "本人"
                    if "本人" in title:
                        title = title.replace("本人", "")
                    elif "配偶" in title:
                        relationship = "配偶"
                        title = title.replace("配偶", "")

                    name = str(row[1]).strip() if len(row) > 1 else ""
                    if not name or name == "姓名":
                        continue

                    details.append(SharePledging(
                        stock_id=stock_id,
                        company_name=company_name,
                        year=year,
                        month=month,
                        title=title,
                        relationship=relationship,
                        name=name,
                        shares_at_election=self._parse_int(row[2]) if len(row) > 2 else None,
                        current_shares=self._parse_int(row[3]) if len(row) > 3 else None,
                        pledged_shares=self._parse_int(row[4]) if len(row) > 4 else None,
                        pledge_ratio=self._parse_percentage(row[5]) if len(row) > 5 else None,
                    ))
                except Exception as e:
                    logger.debug(f"Failed to parse pledging row: {e}")
                    continue

        return details

    def _parse_pledging_summary(
        self,
        dfs: list,
        stock_id: str,
        company_name: str,
        year: int,
        month: int,
    ) -> Optional[PledgingSummary]:
        for df in dfs:
            if "全體董監持股合計" not in df.to_string():
                continue

            summary = PledgingSummary(
                stock_id=stock_id, company_name=company_name, year=year, month=month
            )

            for idx, row in df.iterrows():
                row_str = str(row[0])
                if "非獨立董事持股合計" in row_str:
                    summary.non_independent_director_shares = self._parse_int(row[1])
                elif "非獨立董事持股設質合計" in row_str:
                    summary.non_independent_director_pledged = self._parse_int(row[1])
                elif "非獨立董事持股設質比例" in row_str:
                    summary.non_independent_director_ratio = self._parse_percentage(row[1])
                elif "獨立董事持股合計" in row_str:
                    summary.independent_director_shares = self._parse_int(row[1])
                elif "獨立董事持股設質合計" in row_str:
                    summary.independent_director_pledged = self._parse_int(row[1])
                elif "獨立董事持股設質比例" in row_str:
                    summary.independent_director_ratio = self._parse_percentage(row[1])
                elif "全體董監持股合計" in row_str:
                    summary.total_shares = self._parse_int(row[1])
                elif "全體董監持股設質合計" in row_str:
                    summary.total_pledged = self._parse_int(row[1])
                elif "全體董監持股設質比例" in row_str:
                    summary.total_pledge_ratio = self._parse_percentage(row[1])

            return summary

        return None

    def _parse_int(self, value) -> Optional[int]:
        if value is None:
            return None
        str_val = str(value).strip()
        if str_val in ['', '-', 'nan', 'NaN', '不適用']:
            return None
        try:
            return int(float(str_val.replace(',', '').replace(' ', '')))
        except (ValueError, TypeError):
            return None

    def _parse_percentage(self, value) -> Optional[float]:
        if value is None:
            return None
        str_val = str(value).strip()
        if str_val in ['', '-', 'nan', 'NaN']:
            return None
        try:
            return round(float(str_val.replace('%', '').replace(',', '').strip()), 2)
        except (ValueError, TypeError):
            return None
