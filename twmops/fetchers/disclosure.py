"""
DisclosureFetcher — fetches funds lending and endorsement/guarantee disclosures from MOPS.
MOPS AJAX endpoint: ajax_t05st11
"""

import logging
import re
from typing import Optional, List

from twmops.models.disclosure import (
    FundsLending,
    EndorsementGuarantee,
    CrossCompanyGuarantee,
    ChinaGuarantee,
    DisclosureResponse,
)
from twmops.utils.numerics import parse_financial_value
from twmops.clients.html_client import (
    MOPSHTMLClient,
    MOPSHTMLClientError,
    MOPSDataNotFoundError,
)

logger = logging.getLogger(__name__)


class DisclosureFetcherError(Exception):
    pass


class DisclosureFetcher:
    """
    Fetch major disclosure data (funds lending, endorsement/guarantee) from MOPS.

    Usage (sync):
        fetcher = DisclosureFetcher()
        data = fetcher.get_disclosure("2317", year=113, month=3)

    Usage (async):
        fetcher = DisclosureFetcher()
        data = await fetcher.get_disclosure_async("2317", year=113, month=3)
    """

    AJAX_ENDPOINT = "ajax_t05st11"

    def __init__(self, html_client: Optional[MOPSHTMLClient] = None):
        self.client = html_client or MOPSHTMLClient()

    def _get_disclosure_params(
        self, stock_id: str, year: int, month: int, market: str
    ) -> dict:
        return {
            "encodeURIComponent": 1,
            "step": 1,
            "firstin": 1,
            "off": 1,
            "TYPEK": market,
            "year": year,
            "month": month,
            "co_id": stock_id,
        }

    def _handle_disclosure_error(self, e: MOPSHTMLClientError, stock_id: str) -> None:
        if isinstance(e, MOPSDataNotFoundError):
            raise DisclosureFetcherError(f"No disclosure data for {stock_id}")
        raise DisclosureFetcherError(f"Failed to fetch disclosure: {e.message}")

    def get_disclosure(
        self,
        stock_id: str,
        year: int,
        month: int,
        market: str = "sii",
    ) -> DisclosureResponse:
        """
        Fetch disclosure data for a company (synchronous version).

        Args:
            stock_id: Stock ID (e.g., "2317")
            year: ROC year (民國年)
            month: Month (1–12)
            market: "sii" or "otc"
        """
        params = self._get_disclosure_params(stock_id, year, month, market)
        logger.info(f"Fetching disclosure data: {stock_id} {year}/{month}")

        try:
            dfs = self.client.fetch_html_table(
                self.AJAX_ENDPOINT, params, method="POST", encoding="utf-8"
            )
        except MOPSHTMLClientError as e:
            self._handle_disclosure_error(e, stock_id)

        return self._parse_disclosure(dfs, stock_id, year, month)

    async def get_disclosure_async(
        self,
        stock_id: str,
        year: int,
        month: int,
        market: str = "sii",
    ) -> DisclosureResponse:
        """
        Fetch disclosure data for a company (asynchronous version).

        Args:
            stock_id: Stock ID (e.g., "2317")
            year: ROC year (民國年)
            month: Month (1–12)
            market: "sii" or "otc"
        """
        params = self._get_disclosure_params(stock_id, year, month, market)
        logger.info(f"Fetching disclosure data: {stock_id} {year}/{month}")

        try:
            dfs = await self.client.fetch_html_table_async(
                self.AJAX_ENDPOINT, params, method="POST", encoding="utf-8"
            )
        except MOPSHTMLClientError as e:
            self._handle_disclosure_error(e, stock_id)

        return self._parse_disclosure(dfs, stock_id, year, month)

    def _parse_disclosure(
        self,
        dfs: list,
        stock_id: str,
        year: int,
        month: int,
    ) -> DisclosureResponse:
        """Parse raw DataFrames into DisclosureResponse."""
        company_name = self._extract_company_name(dfs)
        funds_lending = self._parse_funds_lending(dfs)
        endorsement = self._parse_endorsement(dfs)
        cross_company = self._parse_cross_company(dfs)
        china_guarantee = self._parse_china_guarantee(dfs)

        logger.info(
            f"Parsed disclosure for {stock_id}: {len(funds_lending)} lending, {len(endorsement)} guarantee"
        )

        return DisclosureResponse(
            stock_id=stock_id,
            company_name=company_name,
            year=year,
            month=month,
            funds_lending=funds_lending,
            endorsement_guarantee=endorsement,
            cross_company=cross_company,
            china_guarantee=china_guarantee,
        )

    def _extract_company_name(self, dfs: list) -> str:
        for df in dfs:
            if df.shape[0] > 0:
                val = str(df.iloc[0, 0])
                if "公司" in val:
                    match = re.search(r"\)\s*(.+?)\s*公司", val)
                    if match:
                        return match.group(1)
        return ""

    def _parse_funds_lending(self, dfs: list) -> List[FundsLending]:
        results = []
        for df in dfs:
            if "資金貸放餘額" not in df.to_string():
                continue
            for idx, row in df.iterrows():
                try:
                    first_col = str(row.iloc[0])
                    if "資金貸放餘額" not in first_col:
                        continue
                    entity = "本公司" if "本公司" in first_col else "子公司"
                    has_balance = "有" in first_col
                    results.append(
                        FundsLending(
                            entity=entity,
                            has_balance=has_balance,
                            current_month=self._parse_int(row.iloc[1])
                            if len(row) > 1
                            else None,
                            previous_month=self._parse_int(row.iloc[2])
                            if len(row) > 2
                            else None,
                            max_limit=self._parse_int(row.iloc[3])
                            if len(row) > 3
                            else None,
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse funds lending row: {e}")
        return results

    def _parse_endorsement(self, dfs: list) -> List[EndorsementGuarantee]:
        results = []
        for df in dfs:
            df_str = df.to_string()
            if "背書保證資訊" not in df_str or "大陸" in df_str or "子公司間" in df_str:
                continue
            for idx, row in df.iterrows():
                try:
                    first_col = str(row.iloc[0])
                    if "背書保證資訊" not in first_col:
                        continue
                    entity = "本公司" if "本公司 " in first_col else "子公司"
                    has_balance = "有" in first_col
                    results.append(
                        EndorsementGuarantee(
                            entity=entity,
                            has_balance=has_balance,
                            monthly_change=self._parse_int(row.iloc[1])
                            if len(row) > 1
                            else None,
                            accumulated_balance=self._parse_int(row.iloc[2])
                            if len(row) > 2
                            else None,
                            max_limit=self._parse_int(row.iloc[3])
                            if len(row) > 3
                            else None,
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse endorsement row: {e}")
        return results

    def _parse_cross_company(self, dfs: list) -> Optional[CrossCompanyGuarantee]:
        for df in dfs:
            if "本公司與子公司間" not in df.to_string():
                continue
            p_to_s = None
            s_to_p = None
            for idx, row in df.iterrows():
                first_col = str(row.iloc[0])
                if "本公司對子公司" in first_col:
                    p_to_s = self._parse_int(row.iloc[1]) if len(row) > 1 else None
                elif "子公司對本公司" in first_col:
                    s_to_p = self._parse_int(row.iloc[1]) if len(row) > 1 else None
            if p_to_s is not None or s_to_p is not None:
                return CrossCompanyGuarantee(
                    parent_to_subsidiary=p_to_s, subsidiary_to_parent=s_to_p
                )
        return None

    def _parse_china_guarantee(self, dfs: list) -> List[ChinaGuarantee]:
        results = []
        for df in dfs:
            if "對大陸地區" not in df.to_string():
                continue
            for idx, row in df.iterrows():
                try:
                    first_col = str(row.iloc[0])
                    if "大陸地區" not in first_col:
                        continue
                    entity = "本公司" if "本公司" in first_col else "子公司"
                    has_balance = "有" in first_col
                    results.append(
                        ChinaGuarantee(
                            entity=entity,
                            has_balance=has_balance,
                            monthly_change=self._parse_int(row.iloc[1])
                            if len(row) > 1
                            else None,
                            accumulated_balance=self._parse_int(row.iloc[2])
                            if len(row) > 2
                            else None,
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to parse china guarantee row: {e}")
        return results

    def _parse_int(self, value) -> Optional[int]:
        d = parse_financial_value(value)
        return int(d) if d is not None else None
