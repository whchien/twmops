"""Tests for twmops model classes."""
import pytest
from datetime import datetime
from decimal import Decimal
from pydantic import ValidationError

from twmops.models import (
    MonthlyRevenue,
    FinancialItem,
    FinancialStatement,
    DividendRecord,
    DividendSummary,
    DividendResponse,
    DisclosureResponse,
)
from twmops.models.simplified import (
    SimplifiedFinancialItem,
    SimplifiedFinancialStatement,
    get_statement_mapping,
)
from twmops.models.xbrl import (
    CalculationArc,
    PresentationArc,
    XBRLFact,
    XBRLContext,
    XBRLPackage,
)
from twmops.fetchers.insiders import SharePledging, PledgingSummary, PledgingResponse

pytestmark = pytest.mark.unit


class TestMonthlyRevenue:
    """Test MonthlyRevenue model."""

    def test_create_valid_revenue(self):
        rev = MonthlyRevenue(
            stock_id="2330",
            company_name="台積電",
            year=113,
            month=3,
            revenue=500000,
            revenue_last_month=480000,
            revenue_last_year=510000,
            mom_change=4.17,
            yoy_change=-1.96,
        )
        assert rev.stock_id == "2330"
        assert rev.company_name == "台積電"
        assert rev.revenue == 500000

    def test_optional_fields(self):
        rev = MonthlyRevenue(
            stock_id="2330",
            company_name="台積電",
            year=113,
            month=3,
        )
        assert rev.accumulated_revenue is None
        assert rev.comment is None

    def test_required_fields(self):
        """Missing required fields should raise ValidationError."""
        with pytest.raises(ValidationError):
            MonthlyRevenue(stock_id="2330", company_name="台積電")


class TestFinancialStatement:
    """Test FinancialItem and FinancialStatement models."""

    def test_create_financial_item(self):
        item = FinancialItem(
            account_code="2100",
            account_name="流動資產",
            value=Decimal("100000"),
            level=0,
        )
        assert item.account_code == "2100"
        assert item.account_name == "流動資產"
        assert item.value == Decimal("100000")

    def test_financial_item_with_children(self):
        parent = FinancialItem(
            account_code="2100",
            account_name="流動資產",
            value=Decimal("100000"),
            children=[
                FinancialItem(
                    account_code="1100",
                    account_name="現金",
                    value=Decimal("50000"),
                ),
                FinancialItem(
                    account_code="1200",
                    account_name="應收帳款",
                    value=Decimal("30000"),
                ),
            ],
        )
        assert len(parent.children) == 2
        assert parent.children[0].account_name == "現金"

    def test_create_financial_statement(self):
        stmt = FinancialStatement(
            stock_id="2330",
            year=113,
            quarter=1,
            report_type="balance_sheet",
            items=[
                FinancialItem(
                    account_code="2100",
                    account_name="流動資產",
                    value=Decimal("100000"),
                ),
            ],
        )
        assert stmt.stock_id == "2330"
        assert len(stmt.items) == 1


class TestDividendRecord:
    """Test DividendRecord and DividendResponse models."""

    def test_create_dividend_record(self):
        rec = DividendRecord(
            stock_id="2330",
            company_name="台積電",
            year=113,
            ex_dividend_date="2024-05-15",
            cash_dividend=8.00,
            stock_dividend=0.00,
        )
        assert rec.stock_id == "2330"
        assert rec.year == 113
        assert rec.cash_dividend == 8.00

    def test_create_dividend_summary(self):
        summary = DividendSummary(
            stock_id="2330",
            company_name="台積電",
            year=113,
            total_cash_dividend=16.00,
            total_stock_dividend=0.00,
        )
        assert summary.stock_id == "2330"
        assert summary.year == 113
        assert summary.total_cash_dividend == 16.00

    def test_dividend_response(self):
        resp = DividendResponse(
            stock_id="2330",
            company_name="台積電",
            year_start=110,
            year_end=113,
            count=1,
            records=[
                DividendRecord(
                    stock_id="2330",
                    company_name="台積電",
                    year=113,
                    ex_dividend_date="2024-05-15",
                    cash_dividend=8.00,
                ),
            ],
        )
        assert resp.stock_id == "2330"
        assert len(resp.records) == 1


class TestDisclosureResponse:
    """Test DisclosureResponse model."""

    def test_create_disclosure_response(self):
        resp = DisclosureResponse(
            stock_id="2330",
            company_name="台積電",
            year=113,
            month=3,
        )
        assert resp.stock_id == "2330"
        assert resp.year == 113
        assert resp.month == 3

    def test_disclosure_with_details(self):
        from twmops.models.disclosure import FundsLending

        resp = DisclosureResponse(
            stock_id="2330",
            company_name="台積電",
            year=113,
            month=3,
            funds_lending=[
                FundsLending(entity="Other Company", has_balance=True, current_month=100),
            ],
        )
        assert len(resp.funds_lending) == 1


class TestSimplifiedModels:
    """Test simplified financial statement models."""

    def test_get_statement_mapping_income_statement(self):
        """Test income statement mapping."""
        mapping = get_statement_mapping("income_statement")
        assert isinstance(mapping, dict)
        assert "Revenue" in mapping
        assert mapping["Revenue"] == "Revenue"
        assert "OperatingIncome" in mapping

    def test_get_statement_mapping_balance_sheet(self):
        """Test balance sheet mapping."""
        mapping = get_statement_mapping("balance_sheet")
        assert isinstance(mapping, dict)
        assert "Assets" in mapping
        assert mapping["Assets"] == "TotalAssets"
        assert "Liabilities" in mapping

    def test_get_statement_mapping_cash_flow(self):
        """Test cash flow mapping."""
        mapping = get_statement_mapping("cash_flow")
        assert isinstance(mapping, dict)
        assert "CashFlowsFromUsedInOperatingActivities" in mapping

    def test_get_statement_mapping_unknown(self):
        """Test unknown statement type returns empty dict."""
        mapping = get_statement_mapping("unknown_type")
        assert mapping == {}

    def test_simplified_financial_item(self):
        """Test simplified financial item creation."""
        item = SimplifiedFinancialItem(
            date="2024-03-31",
            stock_id="2330",
            type="Revenue",
            value=1000000.0,
            origin_name="營業收入",
        )
        assert item.stock_id == "2330"
        assert item.type == "Revenue"
        assert item.value == 1000000.0

    def test_simplified_financial_statement(self):
        """Test simplified financial statement creation."""
        stmt = SimplifiedFinancialStatement(
            stock_id="2330",
            year=113,
            quarter=1,
            report_date="2024-03-31",
            statement_type="income_statement",
            items=[
                SimplifiedFinancialItem(
                    date="2024-03-31",
                    stock_id="2330",
                    type="Revenue",
                    value=1000000.0,
                    origin_name="營業收入",
                )
            ],
        )
        assert stmt.stock_id == "2330"
        assert stmt.year == 113
        assert len(stmt.items) == 1


class TestXBRLModels:
    """Test XBRL data models."""

    def test_calculation_arc(self):
        """Test CalculationArc creation."""
        arc = CalculationArc(
            from_concept="Assets",
            to_concept="CurrentAssets",
            weight=1.0,
            order=1.0,
        )
        assert arc.from_concept == "Assets"
        assert arc.to_concept == "CurrentAssets"
        assert arc.weight == 1.0

    def test_presentation_arc(self):
        """Test PresentationArc creation."""
        arc = PresentationArc(
            from_concept="StatementOfComprehensiveIncome",
            to_concept="Revenue",
            order=1.0,
        )
        assert arc.from_concept == "StatementOfComprehensiveIncome"
        assert arc.to_concept == "Revenue"

    def test_xbrl_fact(self):
        """Test XBRLFact creation."""
        fact = XBRLFact(
            concept="Revenue",
            value="1000000",
            context_ref="Current_Period",
            unit="Unit_THD",
        )
        assert fact.concept == "Revenue"
        assert fact.value == "1000000"

    def test_xbrl_context(self):
        """Test XBRLContext creation."""
        ctx = XBRLContext(
            context_id="Current_Period",
            entity="2330",
            instant="2024-03-31",
        )
        assert ctx.context_id == "Current_Period"
        assert ctx.instant == "2024-03-31"

    def test_xbrl_package(self):
        """Test XBRLPackage creation."""
        pkg = XBRLPackage(
            stock_id="2330",
            year=113,
            quarter=1,
            facts=[],
            contexts={},
            calculation_arcs={},
            presentation_arcs={},
        )
        assert pkg.stock_id == "2330"
        assert pkg.year == 113


class TestInsiderModels:
    """Test insider share pledging models."""

    def test_share_pledging(self):
        """Test SharePledging model creation."""
        pledging = SharePledging(
            stock_id="2330",
            company_name="台積電",
            year=113,
            month=3,
            title="董事",
            relationship="本人",
            name="張三",
            shares_at_election=100000,
            current_shares=95000,
            pledged_shares=10000,
            pledge_ratio=10.5,
        )
        assert pledging.stock_id == "2330"
        assert pledging.title == "董事"
        assert pledging.name == "張三"

    def test_share_pledging_optional_fields(self):
        """Test SharePledging with optional fields defaulting to None."""
        pledging = SharePledging(
            stock_id="2330",
            company_name="台積電",
            year=113,
            month=3,
            title="董事",
            relationship="本人",
            name="張三",
        )
        assert pledging.shares_at_election is None
        assert pledging.pledge_ratio is None

    def test_pledging_summary(self):
        """Test PledgingSummary model creation."""
        summary = PledgingSummary(
            stock_id="2330",
            company_name="台積電",
            year=113,
            month=3,
            total_shares=1000000,
            total_pledged=100000,
            total_pledge_ratio=10.0,
        )
        assert summary.stock_id == "2330"
        assert summary.total_shares == 1000000

    def test_pledging_response(self):
        """Test PledgingResponse model creation."""
        response = PledgingResponse(
            stock_id="2330",
            company_name="台積電",
            year=113,
            month=3,
            details=[],
            summary=None,
        )
        assert response.stock_id == "2330"
        assert len(response.details) == 0
