"""
Numeric parsing utilities for financial data
"""

from decimal import Decimal, InvalidOperation
from typing import Optional


def parse_financial_value(value_str: Optional[str]) -> Optional[Decimal]:
    """
    Parse a financial value string to Decimal.

    Handles comma separators, whitespace, em-dash, negative numbers, decimals.

    Examples:
        >>> parse_financial_value("1,234,567")
        Decimal('1234567')
        >>> parse_financial_value("-1,234.56")
        Decimal('-1234.56')
        >>> parse_financial_value("")
        None
        >>> parse_financial_value("-")
        None
    """
    if value_str is None:
        return None

    cleaned = str(value_str).replace(",", "").strip()

    if not cleaned or cleaned in ("-", "—", ""):
        return None

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def is_numeric_string(value_str: Optional[str]) -> bool:
    """
    Check whether a string represents a valid numeric value (fast path, no full parse).

    Supports negative numbers and decimals.
    """
    if value_str is None:
        return False

    cleaned = str(value_str).replace(",", "").strip()
    if not cleaned or cleaned in ("-", "—"):
        return False

    test_str = cleaned.lstrip("-")
    if test_str.count(".") > 1:
        return False

    return test_str.replace(".", "", 1).isdigit()
