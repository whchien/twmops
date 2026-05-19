"""Tests for DisclosureFetcher."""

import pytest
import pandas as pd
from unittest.mock import Mock, AsyncMock, patch
from httpx import Response

from twmops.fetchers.disclosure import DisclosureFetcher, DisclosureFetcherError
from twmops.clients.html_client import MOPSDataNotFoundError, MOPSHTMLClientError

pytestmark = pytest.mark.unit


class TestDisclosureFetcher:
    """Test DisclosureFetcher initialization and error handling."""

    def test_fetcher_initialization(self):
        """Test DisclosureFetcher can be instantiated."""
        fetcher = DisclosureFetcher()
        assert fetcher is not None
        assert hasattr(fetcher, "client")
        assert hasattr(fetcher, "get_disclosure")
        assert hasattr(fetcher, "get_disclosure_async")

    def test_fetcher_has_methods(self):
        """Test that fetcher has required methods."""
        fetcher = DisclosureFetcher()
        assert callable(fetcher.get_disclosure)
        assert callable(fetcher.get_disclosure_async)

    def test_fetcher_with_custom_client(self):
        """Test initializing fetcher with custom client."""
        mock_client = Mock()
        fetcher = DisclosureFetcher(html_client=mock_client)
        assert fetcher.client == mock_client

    @pytest.mark.parametrize(
        "stock_id,year,month,market",
        [
            ("2330", 113, 1, "sii"),
            ("2330", 113, 6, "otc"),
            ("2412", 112, 12, "sii"),
        ],
    )
    def test_fetcher_accepts_valid_parameters(self, stock_id, year, month, market):
        """Test that fetcher accepts valid parameters."""
        fetcher = DisclosureFetcher()
        assert fetcher is not None
        assert isinstance(stock_id, str)
        assert isinstance(year, int)
        assert 1 <= month <= 12
        assert market in ("sii", "otc")

    @pytest.mark.asyncio
    async def test_fetcher_async_method_exists(self):
        """Test that async method exists and is callable."""
        fetcher = DisclosureFetcher()
        assert callable(fetcher.get_disclosure_async)

    def test_disclosure_fetcher_error_exists(self):
        """Test that DisclosureFetcherError exists."""
        assert DisclosureFetcherError is not None
        # Can be raised as exception
        with pytest.raises(DisclosureFetcherError):
            raise DisclosureFetcherError("test")


class TestDisclosureParsing:
    """Test DisclosureFetcher parsing logic."""

    def test_parse_funds_lending_with_balance(self):
        """Test parsing funds lending data."""
        fetcher = DisclosureFetcher()
        df = pd.DataFrame(
            [
                ["本公司 資金貸放餘額有", "1000", "950", "5000"],
                ["子公司 資金貸放餘額有", "500", "480", "2000"],
            ],
            columns=["description", "current", "previous", "limit"],
        )

        results = fetcher._parse_funds_lending([df])
        assert len(results) == 2
        assert results[0].entity == "本公司"
        assert results[0].has_balance is True
        assert results[0].current_month == 1000
        assert results[1].entity == "子公司"

    def test_parse_funds_lending_empty(self):
        """Test funds lending parsing with no matching keyword."""
        fetcher = DisclosureFetcher()
        df = pd.DataFrame([["other", "data"]], columns=["col1", "col2"])

        results = fetcher._parse_funds_lending([df])
        assert results == []

    def test_parse_endorsement(self):
        """Test parsing endorsement/guarantee data."""
        fetcher = DisclosureFetcher()
        df = pd.DataFrame(
            [
                ["本公司  背書保證資訊有", "100", "2000", "10000"],
            ],
            columns=["description", "monthly", "accumulated", "limit"],
        )

        results = fetcher._parse_endorsement([df])
        assert len(results) == 1
        assert results[0].entity == "本公司"
        assert results[0].has_balance is True
        assert results[0].monthly_change == 100

    def test_parse_cross_company(self):
        """Test parsing cross-company guarantee data."""
        fetcher = DisclosureFetcher()
        df = pd.DataFrame(
            [
                ["本公司與子公司間 背書保證資訊", ""],
                ["本公司對子公司", "5000"],
                ["子公司對本公司", "2000"],
            ],
            columns=["description", "amount"],
        )

        result = fetcher._parse_cross_company([df])
        assert result is not None
        assert result.parent_to_subsidiary == 5000
        assert result.subsidiary_to_parent == 2000

    def test_parse_cross_company_empty(self):
        """Test cross-company parsing with no matching keyword."""
        fetcher = DisclosureFetcher()
        df = pd.DataFrame([["other", "data"]], columns=["col1", "col2"])

        result = fetcher._parse_cross_company([df])
        assert result is None

    def test_parse_china_guarantee(self):
        """Test parsing China guarantee data."""
        fetcher = DisclosureFetcher()
        df = pd.DataFrame(
            [
                ["本公司 對大陸地區 背書保證資訊有", "500", "3000"],
            ],
            columns=["description", "monthly", "accumulated"],
        )

        results = fetcher._parse_china_guarantee([df])
        assert len(results) == 1
        assert results[0].entity == "本公司"
        assert results[0].has_balance is True

    def test_get_disclosure_sync(self):
        """Test synchronous disclosure fetching with mocked client."""
        fetcher = DisclosureFetcher()
        mock_client = Mock()
        fetcher.client = mock_client

        # Mock DataFrame response
        dfs = [
            pd.DataFrame(
                [
                    ["2330 台積電"],
                    ["本公司 資金貸放餘額有", "1000", "950", "5000"],
                ],
                columns=["col1", "col2", "col3", "col4"],
            )
        ]
        mock_client.fetch_html_table.return_value = dfs

        response = fetcher.get_disclosure("2330", year=113, month=3)
        assert response.stock_id == "2330"
        assert response.year == 113
        assert response.month == 3
        mock_client.fetch_html_table.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_disclosure_async(self):
        """Test asynchronous disclosure fetching with mocked client."""
        fetcher = DisclosureFetcher()
        mock_client = AsyncMock()
        fetcher.client = mock_client

        dfs = [pd.DataFrame([["2330 台積電"]], columns=["col1"])]
        mock_client.fetch_html_table_async.return_value = dfs

        response = await fetcher.get_disclosure_async("2330", year=113, month=3)
        assert response.stock_id == "2330"
        mock_client.fetch_html_table_async.assert_called_once()

    def test_get_disclosure_not_found_error(self):
        """Test error handling when disclosure data not found."""
        fetcher = DisclosureFetcher()
        mock_client = Mock()
        fetcher.client = mock_client
        mock_client.fetch_html_table.side_effect = MOPSDataNotFoundError("No data")

        with pytest.raises(DisclosureFetcherError, match="No disclosure data"):
            fetcher.get_disclosure("9999", year=113, month=3)

    def test_get_disclosure_client_error(self):
        """Test error handling for general client errors."""
        fetcher = DisclosureFetcher()
        mock_client = Mock()
        fetcher.client = mock_client

        class CustomError(MOPSHTMLClientError):
            def __init__(self):
                self.message = "Connection error"

        mock_client.fetch_html_table.side_effect = CustomError()

        with pytest.raises(DisclosureFetcherError, match="Failed to fetch disclosure"):
            fetcher.get_disclosure("2330", year=113, month=3)
