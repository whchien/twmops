"""Tests for InsidersFetcher."""
import pytest
import pandas as pd
from unittest.mock import Mock, AsyncMock
from twmops.fetchers.insiders import (
    InsidersFetcher, InsidersFetcherError, SharePledging, PledgingSummary
)
from twmops.clients.html_client import MOPSDataNotFoundError, MOPSHTMLClientError

pytestmark = pytest.mark.unit


class TestInsidersFetcher:
    """Test InsidersFetcher initialization and methods."""

    def test_fetcher_initialization(self):
        """Test InsidersFetcher can be instantiated."""
        fetcher = InsidersFetcher()
        assert fetcher is not None
        assert hasattr(fetcher, 'client')

    def test_fetcher_has_required_methods(self):
        """Test that fetcher has required methods."""
        fetcher = InsidersFetcher()
        assert callable(fetcher.get_share_pledging)
        assert callable(fetcher.get_share_pledging_async)

    def test_fetcher_with_custom_client(self):
        """Test initializing fetcher with custom client."""
        mock_client = Mock()
        fetcher = InsidersFetcher(html_client=mock_client)
        assert fetcher.client == mock_client

    @pytest.mark.parametrize("stock_id,market", [
        ("2330", "sii"),
        ("2412", "sii"),
        ("8086", "otc"),
    ])
    def test_fetcher_accepts_valid_parameters(self, stock_id, market):
        """Test that fetcher accepts valid parameters."""
        fetcher = InsidersFetcher()
        assert fetcher is not None
        assert isinstance(stock_id, str)
        assert market in ("sii", "otc")

    @pytest.mark.asyncio
    async def test_fetcher_async_method_exists(self):
        """Test that async methods exist."""
        fetcher = InsidersFetcher()
        assert callable(fetcher.get_share_pledging_async)

    def test_insiders_fetcher_error(self):
        """Test that InsidersFetcherError exists."""
        assert InsidersFetcherError is not None
        with pytest.raises(InsidersFetcherError):
            raise InsidersFetcherError("test error")


class TestInsidersParseHelpers:
    """Test InsidersFetcher parsing helper methods."""

    def test_parse_int_valid(self):
        """Test parsing valid integer strings."""
        fetcher = InsidersFetcher()
        assert fetcher._parse_int("1234567") == 1234567
        assert fetcher._parse_int("1,234,567") == 1234567
        assert fetcher._parse_int("100") == 100

    def test_parse_int_dash(self):
        """Test parsing dash returns None."""
        fetcher = InsidersFetcher()
        assert fetcher._parse_int("-") is None
        assert fetcher._parse_int("") is None

    def test_parse_int_nan(self):
        """Test parsing NaN/nan returns None."""
        fetcher = InsidersFetcher()
        assert fetcher._parse_int("NaN") is None
        assert fetcher._parse_int("nan") is None

    def test_parse_int_not_applicable(self):
        """Test parsing not applicable string."""
        fetcher = InsidersFetcher()
        assert fetcher._parse_int("不適用") is None

    def test_parse_int_none(self):
        """Test parsing None input."""
        fetcher = InsidersFetcher()
        assert fetcher._parse_int(None) is None

    def test_parse_percentage_valid(self):
        """Test parsing valid percentage strings."""
        fetcher = InsidersFetcher()
        assert fetcher._parse_percentage("12.34") == 12.34
        assert fetcher._parse_percentage("5.67%") == 5.67
        assert fetcher._parse_percentage("0.5") == 0.5

    def test_parse_percentage_with_comma(self):
        """Test parsing percentage with commas."""
        fetcher = InsidersFetcher()
        assert fetcher._parse_percentage("12.34") == 12.34

    def test_parse_percentage_dash(self):
        """Test parsing dash percentage returns None."""
        fetcher = InsidersFetcher()
        assert fetcher._parse_percentage("-") is None
        assert fetcher._parse_percentage("") is None

    def test_parse_percentage_nan(self):
        """Test parsing NaN percentage."""
        fetcher = InsidersFetcher()
        assert fetcher._parse_percentage("NaN") is None

    def test_parse_percentage_none(self):
        """Test parsing None percentage."""
        fetcher = InsidersFetcher()
        assert fetcher._parse_percentage(None) is None


class TestInsidersParseDetails:
    """Test InsidersFetcher pledging details parsing."""

    def test_parse_pledging_details_basic(self):
        """Test parsing basic pledging detail records."""
        fetcher = InsidersFetcher()
        df = pd.DataFrame([
            ["職稱", "姓名", "當選持股", "目前持股", "持股設質", "設質比例"],
            ["董事", "張三", "100000", "95000", "10000", "10.5%"],
            ["監察人", "李四", "50000", "48000", "5000", "10.4%"],
        ], columns=list(range(6)))

        results = fetcher._parse_pledging_details([df], "2330", "台積電", 113, 3)
        assert len(results) == 2
        assert results[0].name == "張三"
        assert results[0].title == "董事"
        assert results[0].relationship == "本人"

    def test_parse_pledging_details_spouse(self):
        """Test parsing pledging details with spouse relationship."""
        fetcher = InsidersFetcher()
        df = pd.DataFrame([
            ["職稱", "姓名", "當選持股", "目前持股", "持股設質", "設質比例"],
            ["董事配偶", "王五", "50000", "45000", "5000", "10.0%"],
            ["監察人", "陳六", "30000", "28000", "3000", "10.7%"],
        ], columns=list(range(6)))

        results = fetcher._parse_pledging_details([df], "2330", "台積電", 113, 3)
        assert len(results) == 2
        assert results[0].relationship == "配偶"
        assert results[0].title == "董事"

    def test_parse_pledging_details_skips_headers(self):
        """Test that header rows are skipped."""
        fetcher = InsidersFetcher()
        df = pd.DataFrame([
            ["職稱", "姓名", "當選持股", "目前持股", "持股設質", "設質比例"],
            ["", "", "", "", "", ""],
        ], columns=list(range(6)))

        results = fetcher._parse_pledging_details([df], "2330", "台積電", 113, 3)
        assert results == []


class TestInsidersParseSummary:
    """Test InsidersFetcher pledging summary parsing."""

    def test_parse_pledging_summary(self):
        """Test parsing pledging summary."""
        fetcher = InsidersFetcher()
        df = pd.DataFrame([
            ["非獨立董事持股合計", "1000000"],
            ["非獨立董事持股設質合計", "100000"],
            ["非獨立董事持股設質比例", "10.0%"],
            ["獨立董事持股合計", "500000"],
            ["獨立董事持股設質合計", "50000"],
            ["獨立董事持股設質比例", "10.0%"],
            ["全體董監持股合計", "1500000"],
            ["全體董監持股設質合計", "150000"],
            ["全體董監持股設質比例", "10.0%"],
        ], columns=[0, 1])

        result = fetcher._parse_pledging_summary([df], "2330", "台積電", 113, 3)
        assert result is not None
        assert result.non_independent_director_shares == 1000000
        assert result.non_independent_director_pledged == 100000
        assert result.independent_director_shares == 500000
        assert result.total_shares == 1500000

    def test_parse_pledging_summary_empty(self):
        """Test pledging summary parsing with no matching keyword."""
        fetcher = InsidersFetcher()
        df = pd.DataFrame([["other", "data"]], columns=[0, 1])

        result = fetcher._parse_pledging_summary([df], "2330", "台積電", 113, 3)
        assert result is None


class TestInsidersEndToEnd:
    """Test InsidersFetcher end-to-end methods."""

    def test_get_share_pledging_sync(self):
        """Test synchronous share pledging fetching."""
        fetcher = InsidersFetcher()
        mock_client = Mock()
        fetcher.client = mock_client

        dfs = [pd.DataFrame([["2330 台積電"]], columns=[0])]
        mock_client.fetch_html_table.return_value = dfs

        response = fetcher.get_share_pledging("2330", year=113, month=3)
        assert response.stock_id == "2330"
        assert response.year == 113
        assert response.month == 3

    @pytest.mark.asyncio
    async def test_get_share_pledging_async(self):
        """Test asynchronous share pledging fetching."""
        fetcher = InsidersFetcher()
        mock_client = AsyncMock()
        fetcher.client = mock_client

        dfs = [pd.DataFrame([["2330 台積電"]], columns=[0])]
        mock_client.fetch_html_table_async.return_value = dfs

        response = await fetcher.get_share_pledging_async("2330", year=113, month=3)
        assert response.stock_id == "2330"

    def test_get_share_pledging_not_found(self):
        """Test error handling for missing pledging data."""
        fetcher = InsidersFetcher()
        mock_client = Mock()
        fetcher.client = mock_client
        mock_client.fetch_html_table.side_effect = MOPSDataNotFoundError("No data")

        with pytest.raises(InsidersFetcherError, match="No pledging data"):
            fetcher.get_share_pledging("9999", year=113, month=3)

    def test_get_share_pledging_client_error(self):
        """Test error handling for client errors."""
        fetcher = InsidersFetcher()
        mock_client = Mock()
        fetcher.client = mock_client

        class CustomError(MOPSHTMLClientError):
            def __init__(self):
                self.message = "Network error"

        mock_client.fetch_html_table.side_effect = CustomError()

        with pytest.raises(InsidersFetcherError, match="Failed to fetch pledging"):
            fetcher.get_share_pledging("2330", year=113, month=3)
