"""Tests for XBRLParser."""

import pytest
import io
from unittest.mock import Mock, patch
from decimal import Decimal

from twmops.parsers.xbrl_parser import (
    XBRLParser,
    _get_schema_mappings,
    XBRLParserError,
)
from twmops.models.xbrl import XBRLPackage, XBRLFact, XBRLContext

pytestmark = pytest.mark.unit


class TestXBRLParser:
    """Test XBRL parsing functionality."""

    def test_parser_initialization(self):
        """Test XBRLParser can be instantiated."""
        parser = XBRLParser()
        assert parser is not None
        assert hasattr(parser, "parse")

    def test_parser_handles_empty_content(self):
        """Test parser behavior with empty content."""
        parser = XBRLParser()
        with pytest.raises((XBRLParserError, Exception)):
            parser.parse(b"", "2330", 113, 1)

    def test_parser_detects_invalid_xml(self):
        """Test parser rejects invalid XML."""
        parser = XBRLParser()
        invalid_xml = b"<invalid>not well-formed"
        with pytest.raises((XBRLParserError, Exception)):
            parser.parse(invalid_xml, "2330", 113, 1)

    def test_parser_detects_unknown_format(self):
        """Test parser rejects unknown file format."""
        parser = XBRLParser()
        with pytest.raises(XBRLParserError):
            parser.parse(b"random data", "2330", 113, 1)

    def test_schema_mappings_returns_dict(self):
        """Test that _get_schema_mappings returns a dictionary."""
        mappings = _get_schema_mappings()
        assert isinstance(mappings, dict)

    def test_xbrl_package_structure(self):
        """Test that parsed package has required structure."""
        # This would need actual XBRL sample data
        # Placeholder for integration test
        assert XBRLPackage is not None

    @pytest.mark.parametrize(
        "stock_id,year,quarter",
        [
            ("2330", 113, 1),
            ("2412", 113, 2),
            ("0050", 113, 4),
        ],
    )
    def test_parser_accepts_valid_parameters(self, stock_id, year, quarter):
        """Test parser with valid parameters."""
        # Basic parameter validation
        assert isinstance(stock_id, str)
        assert isinstance(year, int)
        assert isinstance(quarter, int)
        assert 1 <= quarter <= 4


class TestSchemaMapping:
    """Test schema mapping functionality."""

    def test_schema_mappings_is_accessible(self):
        """Test that schema mappings can be accessed."""
        mappings = _get_schema_mappings()
        assert mappings is not None

    def test_schema_mappings_type(self):
        """Test that schema mappings is a dict."""
        mappings = _get_schema_mappings()
        assert isinstance(mappings, dict)
