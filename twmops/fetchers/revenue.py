"""
RevenueFetcher — fetches and parses monthly revenue data from MOPS.
No database dependency; always fetches directly from MOPS.

URL pattern:
    https://mopsov.twse.com.tw/nas/t21/{market}/t21sc03_{year}_{month}_{company_type}.html
"""
import logging
from typing import Optional, List

from twmops.models.revenue import MonthlyRevenue
from twmops.utils.numerics import parse_financial_value
from twmops.clients.html_client import (
    MOPSHTMLClient,
    MOPSHTMLClientError,
    MOPSDataNotFoundError,
)

logger = logging.getLogger(__name__)


class RevenueFetcherError(Exception):
    pass


class RevenueFetcher:
    """
    Fetch monthly revenue data from MOPS.

    Markets:
    - sii: 上市 (TWSE listed)
    - otc: 上櫃 (OTC)
    - rotc: 興櫃 (Emerging)
    - pub: 公開發行 (Public)

    Usage:
        fetcher = RevenueFetcher()
        revenues = await fetcher.get_market_revenue(year=113, month=3, market="sii")
        tsmc = await fetcher.get_single_revenue("2330", year=113, month=3)
    """

    MARKET_TYPES = {"sii", "otc", "rotc", "pub"}

    def __init__(self, html_client: Optional[MOPSHTMLClient] = None):
        self.client = html_client or MOPSHTMLClient()

    def _validate_market(self, market: str) -> None:
        if market not in self.MARKET_TYPES:
            raise RevenueFetcherError(f"Invalid market: {market}. Must be one of {self.MARKET_TYPES}")

    def _get_revenue_url(self, year: int, month: int, market: str, company_type: int) -> str:
        return self.client.REVENUE_URL_PATTERN.format(
            market=market,
            year=year,
            month=month,
            company_type=company_type,
        )

    def get_market_revenue(
        self,
        year: int,
        month: int,
        market: str = "sii",
        company_type: int = 0,
    ) -> List[MonthlyRevenue]:
        """
        Fetch all companies' monthly revenue for a given market and period (synchronous version).

        Args:
            year: ROC year (民國年, e.g. 113)
            month: Month (1–12)
            market: Market type (sii/otc/rotc/pub)
            company_type: 0 = domestic, 1 = foreign
        """
        self._validate_market(market)
        url = self._get_revenue_url(year, month, market, company_type)
        logger.info(f"Fetching revenue from MOPS: {year}/{month} {market}")

        try:
            dfs = self.client.fetch_static_html(url, encoding="big5")
        except MOPSDataNotFoundError:
            raise RevenueFetcherError(f"No revenue data for {year}/{month}")
        except MOPSHTMLClientError as e:
            raise RevenueFetcherError(f"Failed to fetch revenue: {e.message}")

        return self._parse_revenue_tables(dfs, year, month)

    async def get_market_revenue_async(
        self,
        year: int,
        month: int,
        market: str = "sii",
        company_type: int = 0,
    ) -> List[MonthlyRevenue]:
        """
        Fetch all companies' monthly revenue for a given market and period (asynchronous version).

        Args:
            year: ROC year (民國年, e.g. 113)
            month: Month (1–12)
            market: Market type (sii/otc/rotc/pub)
            company_type: 0 = domestic, 1 = foreign
        """
        self._validate_market(market)
        url = self._get_revenue_url(year, month, market, company_type)
        logger.info(f"Fetching revenue from MOPS: {year}/{month} {market}")

        try:
            dfs = await self.client.fetch_static_html_async(url, encoding="big5")
        except MOPSDataNotFoundError:
            raise RevenueFetcherError(f"No revenue data for {year}/{month}")
        except MOPSHTMLClientError as e:
            raise RevenueFetcherError(f"Failed to fetch revenue: {e.message}")

        return self._parse_revenue_tables(dfs, year, month)

    def get_single_revenue(
        self,
        stock_id: str,
        year: int,
        month: int,
        market: str = "sii",
    ) -> Optional[MonthlyRevenue]:
        """
        Fetch a single company's monthly revenue (synchronous version).

        Args:
            stock_id: Stock ID (e.g., "2330")
            year: ROC year
            month: Month (1–12)
            market: Market type
        """
        revenues = self.get_market_revenue(year, month, market)
        for rev in revenues:
            if rev.stock_id == stock_id:
                return rev
        return None

    async def get_single_revenue_async(
        self,
        stock_id: str,
        year: int,
        month: int,
        market: str = "sii",
    ) -> Optional[MonthlyRevenue]:
        """
        Fetch a single company's monthly revenue (asynchronous version).

        Args:
            stock_id: Stock ID (e.g., "2330")
            year: ROC year
            month: Month (1–12)
            market: Market type
        """
        revenues = await self.get_market_revenue_async(year, month, market)
        for rev in revenues:
            if rev.stock_id == stock_id:
                return rev
        return None


    def _parse_revenue_tables(self, dfs: list, year: int, month: int) -> List[MonthlyRevenue]:
        revenues: List[MonthlyRevenue] = []
        for df in dfs:
            if df.shape[0] < 2 or df.shape[1] < 5:
                continue
            revenues.extend(self._parse_single_table(df, year, month))
        return revenues

    def _parse_single_table(self, df, year: int, month: int) -> List[MonthlyRevenue]:
        revenues = []
        failure_count = 0

        df.columns = range(len(df.columns))

        for idx, row in df.iterrows():
            try:
                stock_id = str(row[0]).strip()

                if not stock_id or len(stock_id) < 4 or stock_id in ['合計', '公司代號', '公司', '合計:']:
                    continue
                if not stock_id[0].isdigit():
                    continue

                company_name = str(row[1]).strip() if len(row) > 1 else ""

                def _p_int(val):
                    d = parse_financial_value(val)
                    return int(d) if d is not None else None

                def _p_float(val):
                    d = parse_financial_value(val)
                    return float(d) if d is not None else None

                revenue = _p_int(row[2]) if len(row) > 2 else None
                revenue_last_month = _p_int(row[3]) if len(row) > 3 else None
                revenue_last_year = _p_int(row[4]) if len(row) > 4 else None
                mom_change = _p_float(row[5]) if len(row) > 5 else None
                yoy_change = _p_float(row[6]) if len(row) > 6 else None
                accumulated_revenue = _p_int(row[7]) if len(row) > 7 else None
                accumulated_last_year = _p_int(row[8]) if len(row) > 8 else None
                accumulated_yoy_change = _p_float(row[9]) if len(row) > 9 else None

                comment_raw = str(row[10]).strip() if len(row) > 10 else ""
                comment = comment_raw if comment_raw not in ['-', 'nan', '', 'None'] else None

                revenues.append(MonthlyRevenue(
                    stock_id=stock_id,
                    company_name=company_name,
                    year=year,
                    month=month,
                    revenue=revenue,
                    revenue_last_month=revenue_last_month,
                    revenue_last_year=revenue_last_year,
                    mom_change=mom_change,
                    yoy_change=yoy_change,
                    accumulated_revenue=accumulated_revenue,
                    accumulated_last_year=accumulated_last_year,
                    accumulated_yoy_change=accumulated_yoy_change,
                    comment=comment if comment and comment != 'nan' else None,
                ))

            except Exception as e:
                failure_count += 1
                if failure_count <= 5:
                    logger.warning(f"Error parsing revenue row {idx}: {e}")
                elif failure_count == 6:
                    logger.warning("Too many parsing errors, suppressing further logs.")
                continue

        if failure_count > 0:
            logger.info(f"Finished parsing table with {failure_count} failed rows.")

        return revenues
