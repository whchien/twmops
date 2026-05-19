"""
FinancialFetcher — downloads XBRL from MOPS and parses into structured financial statements.
No database dependency; always fetches directly from MOPS.
"""

import logging
from typing import Optional, List, Dict

from twmops.models.financial import FinancialStatement, FinancialItem
from twmops.models.xbrl import XBRLPackage, CalculationArc
from twmops.models.simplified import (
    SimplifiedFinancialStatement,
    SimplifiedFinancialItem,
)
from twmops.clients.xbrl_client import MOPSXBRLClient, MOPSXBRLClientError
from twmops.parsers.xbrl_parser import XBRLParser, XBRLParserError
from twmops.utils.numerics import parse_financial_value

logger = logging.getLogger(__name__)


class FinancialFetcherError(Exception):
    pass


class FinancialFetcher:
    """
    Fetch and parse XBRL financial statements from MOPS.

    Usage:
        fetcher = FinancialFetcher()
        stmt = await fetcher.get_financial_statement("2330", year=113, quarter=1)
    """

    REPORT_ROLES = {
        "balance_sheet": "StatementOfFinancialPosition",
        "income_statement": "StatementOfComprehensiveIncome",
        "cash_flow": "StatementOfCashFlows",
        "equity_statement": "StatementOfChangesInEquity",
    }

    def __init__(
        self,
        xbrl_client: Optional[MOPSXBRLClient] = None,
        xbrl_parser: Optional[XBRLParser] = None,
    ):
        self.mops_client = xbrl_client or MOPSXBRLClient()
        self.xbrl_parser = xbrl_parser or XBRLParser()

    def _normalize_quarter(self, quarter: Optional[int]) -> int:
        return quarter if quarter else 4

    def _download_and_parse(
        self, content: bytes, stock_id: str, year: int, quarter: int
    ) -> XBRLPackage:
        try:
            package = self.xbrl_parser.parse(content, stock_id, year, quarter)
        except XBRLParserError as e:
            raise FinancialFetcherError(f"Failed to parse XBRL: {e}")
        return package

    def get_financial_statement(
        self,
        stock_id: str,
        year: int,
        quarter: Optional[int] = None,
        report_type: str = "balance_sheet",
        format: str = "tree",
    ) -> FinancialStatement:
        """
        Download and parse a financial statement from MOPS (synchronous version).

        Args:
            stock_id: Stock ID (e.g., "2330")
            year: ROC year (民國年, e.g. 113)
            quarter: Quarter (1–4); None defaults to Q4 (annual report)
            report_type: balance_sheet | income_statement | cash_flow | equity_statement
            format: "tree" (hierarchical) or "flat" (all items at same level)

        Returns:
            FinancialStatement
        """
        download_quarter = self._normalize_quarter(quarter)

        try:
            content = self.mops_client.download_xbrl(stock_id, year, download_quarter)
        except MOPSXBRLClientError as e:
            raise FinancialFetcherError(f"Failed to download XBRL: {e.message}")

        package = self._download_and_parse(content, stock_id, year, download_quarter)
        statement = self._build_statement(package, report_type)

        if format == "flat":
            statement.items = self._flatten_items(statement.items)

        return statement

    async def get_financial_statement_async(
        self,
        stock_id: str,
        year: int,
        quarter: Optional[int] = None,
        report_type: str = "balance_sheet",
        format: str = "tree",
    ) -> FinancialStatement:
        """
        Download and parse a financial statement from MOPS (asynchronous version).

        Args:
            stock_id: Stock ID (e.g., "2330")
            year: ROC year (民國年, e.g. 113)
            quarter: Quarter (1–4); None defaults to Q4 (annual report)
            report_type: balance_sheet | income_statement | cash_flow | equity_statement
            format: "tree" (hierarchical) or "flat" (all items at same level)

        Returns:
            FinancialStatement
        """
        download_quarter = self._normalize_quarter(quarter)

        try:
            content = await self.mops_client.download_xbrl_async(
                stock_id, year, download_quarter
            )
        except MOPSXBRLClientError as e:
            raise FinancialFetcherError(f"Failed to download XBRL: {e.message}")

        package = self._download_and_parse(content, stock_id, year, download_quarter)
        statement = self._build_statement(package, report_type)

        if format == "flat":
            statement.items = self._flatten_items(statement.items)

        return statement

    def get_simplified_statement(
        self,
        stock_id: str,
        year: int,
        quarter: Optional[int] = None,
        statement_type: str = "income_statement",
    ) -> SimplifiedFinancialStatement:
        """
        Download and parse a financial statement in simplified FinMind-style format (synchronous version).

        Args:
            stock_id: Stock ID
            year: ROC year
            quarter: Quarter (1–4); None defaults to Q4
            statement_type: income_statement | balance_sheet | cash_flow
        """
        q = self._normalize_quarter(quarter)

        try:
            content = self.mops_client.download_xbrl(stock_id, year, q)
        except MOPSXBRLClientError as e:
            raise FinancialFetcherError(f"Failed to download XBRL: {e.message}")

        package = self._download_and_parse(content, stock_id, year, q)
        return self._convert_to_simplified(package, stock_id, year, q, statement_type)

    async def get_simplified_statement_async(
        self,
        stock_id: str,
        year: int,
        quarter: Optional[int] = None,
        statement_type: str = "income_statement",
    ) -> SimplifiedFinancialStatement:
        """
        Download and parse a financial statement in simplified FinMind-style format (asynchronous version).

        Args:
            stock_id: Stock ID
            year: ROC year
            quarter: Quarter (1–4); None defaults to Q4
            statement_type: income_statement | balance_sheet | cash_flow
        """
        q = self._normalize_quarter(quarter)

        try:
            content = await self.mops_client.download_xbrl_async(stock_id, year, q)
        except MOPSXBRLClientError as e:
            raise FinancialFetcherError(f"Failed to download XBRL: {e.message}")

        package = self._download_and_parse(content, stock_id, year, q)
        return self._convert_to_simplified(package, stock_id, year, q, statement_type)

    def _convert_to_simplified(
        self,
        package: XBRLPackage,
        stock_id: str,
        year: int,
        quarter: int,
        statement_type: str,
    ) -> SimplifiedFinancialStatement:
        western_year = year + 1911
        quarter_month = {1: "03", 2: "06", 3: "09", 4: "12"}
        quarter_day = {1: "31", 2: "30", 3: "30", 4: "31"}
        report_date = f"{western_year}-{quarter_month[quarter]}-{quarter_day[quarter]}"

        simplified_items = []
        seen_types: set = set()

        for fact in package.facts:
            concept = fact.concept
            if concept in seen_types or fact.value is None:
                continue

            parsed = parse_financial_value(fact.value)
            if parsed is None:
                continue

            seen_types.add(concept)
            origin_name = package.labels.get(concept, concept)

            simplified_items.append(
                SimplifiedFinancialItem(
                    date=report_date,
                    stock_id=stock_id,
                    type=concept,
                    value=float(parsed),
                    origin_name=origin_name,
                )
            )

        return SimplifiedFinancialStatement(
            stock_id=stock_id,
            year=year,
            quarter=quarter,
            report_date=report_date,
            statement_type=statement_type,
            items=simplified_items,
        )

    def _build_statement(
        self, package: XBRLPackage, report_type: str
    ) -> FinancialStatement:
        fact_values = {fact.concept: fact.value for fact in package.facts}
        return self._build_statement_with_facts(package, report_type, fact_values)

    def _build_statement_with_facts(
        self,
        package: XBRLPackage,
        report_type: str,
        fact_values: Dict[str, str],
    ) -> FinancialStatement:
        statement = FinancialStatement(
            stock_id=package.stock_id,
            year=package.year,
            quarter=package.quarter,
            report_type=report_type,
        )

        weight_map = self._build_weight_map(package.calculation_arcs)
        items = self._build_tree_from_presentation(
            package.presentation_arcs,
            package.labels,
            package.labels_en,
            fact_values,
            weight_map,
        )
        statement.items = items
        return statement

    def _build_weight_map(
        self,
        calculation_arcs: Dict[str, List[CalculationArc]],
    ) -> Dict[str, float]:
        weight_map: Dict[str, float] = {}
        for parent, arcs in calculation_arcs.items():
            for arc in arcs:
                weight_map[arc.to_concept] = arc.weight
        return weight_map

    def _build_tree_from_presentation(
        self,
        presentation_arcs: Dict[str, list],
        labels_zh: Dict[str, str],
        labels_en: Dict[str, str],
        fact_values: Dict[str, str],
        weight_map: Dict[str, float],
        parent: Optional[str] = None,
        level: int = 0,
        visited: Optional[set] = None,
        max_depth: int = 20,
    ) -> List[FinancialItem]:
        items: List[FinancialItem] = []

        if visited is None:
            visited = set()

        if level > max_depth:
            return items

        if parent is None:
            if not presentation_arcs:
                logger.warning(
                    "No presentation arcs found, falling back to flat facts list"
                )
                fallback_items = []
                for concept, value_str in fact_values.items():
                    value = parse_financial_value(value_str)
                    fallback_items.append(
                        FinancialItem(
                            account_code=concept,
                            account_name=labels_zh.get(concept, concept),
                            account_name_en=labels_en.get(concept),
                            value=value,
                            weight=1.0,
                            level=0,
                            children=[],
                        )
                    )
                fallback_items.sort(key=lambda x: x.account_code)
                return fallback_items

            all_children = set()
            for arcs in presentation_arcs.values():
                for arc in arcs:
                    all_children.add(arc.to_concept)

            root_concepts = set(presentation_arcs.keys()) - all_children
            current_arcs = [
                type("Arc", (), {"to_concept": c, "order": 0})()
                for c in sorted(root_concepts)
            ]
        else:
            current_arcs = presentation_arcs.get(parent, [])

        sorted_arcs = sorted(current_arcs, key=lambda x: x.order)

        for arc in sorted_arcs:
            concept = arc.to_concept
            if concept in visited:
                continue
            visited.add(concept)

            value = parse_financial_value(fact_values.get(concept))
            weight = weight_map.get(concept, 1.0)

            children = self._build_tree_from_presentation(
                presentation_arcs,
                labels_zh,
                labels_en,
                fact_values,
                weight_map,
                parent=concept,
                level=level + 1,
                visited=visited,
                max_depth=max_depth,
            )

            items.append(
                FinancialItem(
                    account_code=concept,
                    account_name=labels_zh.get(concept, concept),
                    account_name_en=labels_en.get(concept),
                    value=value,
                    weight=weight,
                    level=level,
                    children=children,
                )
            )

        return items

    def _flatten_items(
        self,
        items: List[FinancialItem],
        result: Optional[List[FinancialItem]] = None,
    ) -> List[FinancialItem]:
        if result is None:
            result = []
        for item in items:
            flat_item = item.model_copy()
            flat_item.children = []
            result.append(flat_item)
            if item.children:
                self._flatten_items(item.children, result)
        return result
