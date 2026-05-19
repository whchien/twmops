"""Tests for FinancialFetcher."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal

from twmops.fetchers.financial import FinancialFetcher
from twmops.models.xbrl import XBRLPackage
from twmops.models.financial import FinancialStatement, FinancialItem

pytestmark = pytest.mark.unit


class TestFinancialFetcher:
    """Test FinancialFetcher sync and async methods."""

    def test_get_financial_statement_sync(self):
        """Test synchronous financial statement fetching."""
        mock_xbrl_client = Mock()
        mock_xbrl_parser = Mock()

        mock_xbrl_client.download_xbrl.return_value = b"fake_xbrl_content"

        mock_package = XBRLPackage(
            stock_id="2330",
            year=113,
            quarter=1,
            facts=[],
            contexts={},
            calculation_arcs={},
            presentation_arcs={},
            labels={},
        )
        mock_xbrl_parser.parse.return_value = mock_package

        fetcher = FinancialFetcher(xbrl_client=mock_xbrl_client, xbrl_parser=mock_xbrl_parser)

        # Note: The actual fetcher builds statements from the package,
        # which requires more setup. This tests the basic flow.
        with patch.object(fetcher, '_build_statement') as mock_build:
            mock_statement = FinancialStatement(
                stock_id="2330",
                year=113,
                quarter=1,
                report_type="balance_sheet",
                items=[],
            )
            mock_build.return_value = mock_statement

            stmt = fetcher.get_financial_statement("2330", year=113, quarter=1)

            assert stmt.stock_id == "2330"
            assert stmt.year == 113
            mock_xbrl_client.download_xbrl.assert_called_once_with("2330", 113, 1)
            mock_xbrl_parser.parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_financial_statement_async(self):
        """Test asynchronous financial statement fetching."""
        mock_xbrl_client = AsyncMock()
        mock_xbrl_parser = Mock()

        mock_xbrl_client.download_xbrl_async.return_value = b"fake_xbrl_content"

        mock_package = XBRLPackage(
            stock_id="2330",
            year=113,
            quarter=1,
            facts=[],
            contexts={},
            calculation_arcs={},
            presentation_arcs={},
            labels={},
        )
        mock_xbrl_parser.parse.return_value = mock_package

        fetcher = FinancialFetcher(xbrl_client=mock_xbrl_client, xbrl_parser=mock_xbrl_parser)

        with patch.object(fetcher, '_build_statement') as mock_build:
            mock_statement = FinancialStatement(
                stock_id="2330",
                year=113,
                quarter=1,
                report_type="balance_sheet",
                items=[],
            )
            mock_build.return_value = mock_statement

            stmt = await fetcher.get_financial_statement_async("2330", year=113, quarter=1)

            assert stmt.stock_id == "2330"

    def test_normalize_quarter(self):
        """Test quarter normalization."""
        fetcher = FinancialFetcher()

        assert fetcher._normalize_quarter(1) == 1
        assert fetcher._normalize_quarter(2) == 2
        assert fetcher._normalize_quarter(3) == 3
        assert fetcher._normalize_quarter(4) == 4
        assert fetcher._normalize_quarter(None) == 4

    def test_get_simplified_statement(self):
        """Test simplified financial statement fetching."""
        fetcher = FinancialFetcher()

        # Test that the method exists and is callable
        assert hasattr(fetcher, 'get_simplified_statement')
        assert callable(fetcher.get_simplified_statement)

        # Test async version also exists
        assert hasattr(fetcher, 'get_simplified_statement_async')
        assert callable(fetcher.get_simplified_statement_async)

    def test_download_error_handling(self):
        """Test handling of download errors."""
        from twmops.fetchers.financial import FinancialFetcherError
        from twmops.clients.xbrl_client import MOPSXBRLClientError

        mock_xbrl_client = Mock()
        mock_xbrl_parser = Mock()

        mock_xbrl_client.download_xbrl.side_effect = MOPSXBRLClientError("Download failed")

        fetcher = FinancialFetcher(xbrl_client=mock_xbrl_client, xbrl_parser=mock_xbrl_parser)

        with pytest.raises(FinancialFetcherError):
            fetcher.get_financial_statement("2330", year=113, quarter=1)

    def test_parse_error_handling(self):
        """Test handling of XBRL parse errors."""
        from twmops.fetchers.financial import FinancialFetcherError
        from twmops.parsers.xbrl_parser import XBRLParserError

        mock_xbrl_client = Mock()
        mock_xbrl_parser = Mock()

        mock_xbrl_client.download_xbrl.return_value = b"fake_xbrl_content"
        mock_xbrl_parser.parse.side_effect = XBRLParserError("Parse failed")

        fetcher = FinancialFetcher(xbrl_client=mock_xbrl_client, xbrl_parser=mock_xbrl_parser)

        with pytest.raises(FinancialFetcherError):
            fetcher.get_financial_statement("2330", year=113, quarter=1)

    def test_different_report_types(self):
        """Test fetching different report types."""
        mock_xbrl_client = Mock()
        mock_xbrl_parser = Mock()

        mock_xbrl_client.download_xbrl.return_value = b"fake_xbrl_content"
        mock_package = XBRLPackage(
            stock_id="2330", year=113, quarter=1,
            facts=[], contexts={}, calculation_arcs={}, presentation_arcs={}, labels={},
        )
        mock_xbrl_parser.parse.return_value = mock_package

        fetcher = FinancialFetcher(xbrl_client=mock_xbrl_client, xbrl_parser=mock_xbrl_parser)

        for report_type in ["balance_sheet", "income_statement", "cash_flow"]:
            with patch.object(fetcher, '_build_statement') as mock_build:
                mock_build.return_value = FinancialStatement(
                    stock_id="2330", year=113, quarter=1, report_type=report_type, items=[],
                )

                stmt = fetcher.get_financial_statement(
                    "2330", year=113, quarter=1, report_type=report_type
                )
                assert stmt.stock_id == "2330"
