"""Tests for twmops.utils.numerics functions."""

import pytest
from decimal import Decimal

from twmops.utils.numerics import parse_financial_value, is_numeric_string

pytestmark = pytest.mark.unit


class TestParseFinancialValue:
    """Test parse_financial_value function."""

    def test_parse_simple_integer(self):
        assert parse_financial_value("1000") == Decimal("1000")
        assert parse_financial_value("500") == Decimal("500")

    def test_parse_decimal(self):
        assert parse_financial_value("1000.50") == Decimal("1000.50")
        assert parse_financial_value("99.99") == Decimal("99.99")

    def test_parse_negative_sign(self):
        assert parse_financial_value("-1000") == Decimal("-1000")
        assert parse_financial_value("-50.5") == Decimal("-50.5")

    def test_parse_thousands_separator(self):
        """Comma as thousands separator."""
        assert parse_financial_value("1,000") == Decimal("1000")
        assert parse_financial_value("1,000,000") == Decimal("1000000")

    def test_parse_with_spaces(self):
        """Spaces should be stripped."""
        assert parse_financial_value("  1000  ") == Decimal("1000")
        assert parse_financial_value(" -50 ") == Decimal("-50")

    def test_parse_dash_returns_none(self):
        """Dash or em-dash means no value (returns None)."""
        assert parse_financial_value("-") is None
        assert parse_financial_value("–") is None
        assert parse_financial_value("—") is None

    def test_parse_none_on_invalid(self):
        """Invalid strings return None."""
        assert parse_financial_value("abc") is None
        assert parse_financial_value("") is None
        assert parse_financial_value("N/A") is None

    def test_parse_zero(self):
        assert parse_financial_value("0") == Decimal("0")
        assert parse_financial_value("0.00") == Decimal("0.00")


class TestIsNumericString:
    """Test is_numeric_string function."""

    def test_valid_integers(self):
        assert is_numeric_string("123") is True
        assert is_numeric_string("0") is True

    def test_valid_decimals(self):
        assert is_numeric_string("123.45") is True
        assert is_numeric_string("0.5") is True

    def test_valid_with_thousands(self):
        assert is_numeric_string("1,000") is True
        assert is_numeric_string("1,000,000.50") is True

    def test_valid_negative(self):
        assert is_numeric_string("-100") is True
        assert is_numeric_string("-50.5") is True

    def test_dash_not_numeric(self):
        """Dash alone is not numeric."""
        assert is_numeric_string("-") is False
        assert is_numeric_string("–") is False
        assert is_numeric_string("—") is False

    def test_invalid_strings(self):
        assert is_numeric_string("abc") is False
        assert is_numeric_string("123abc") is False
        assert is_numeric_string("") is False
        assert is_numeric_string("N/A") is False

    def test_with_whitespace(self):
        assert is_numeric_string("  123  ") is True
        assert is_numeric_string("  abc  ") is False
