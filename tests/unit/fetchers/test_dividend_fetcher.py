"""Tests for DividendFetcher."""

import pytest
import pandas as pd
from unittest.mock import Mock, AsyncMock
from twmops.fetchers.dividend import DividendFetcher, DividendFetcherError
from twmops.clients.html_client import MOPSDataNotFoundError, MOPSHTMLClientError

pytestmark = pytest.mark.unit


class TestDividendFetcher:
    """Test DividendFetcher initialization and methods."""

    def test_fetcher_initialization(self):
        """Test DividendFetcher can be instantiated."""
        fetcher = DividendFetcher()
        assert fetcher is not None
        assert hasattr(fetcher, "client")

    def test_fetcher_has_required_methods(self):
        """Test that fetcher has required methods."""
        fetcher = DividendFetcher()
        assert callable(fetcher.get_dividends)
        assert callable(fetcher.get_dividends_async)
        assert callable(fetcher.get_annual_summary)

    def test_fetcher_with_custom_client(self):
        """Test initializing fetcher with custom client."""
        mock_client = Mock()
        fetcher = DividendFetcher(html_client=mock_client)
        assert fetcher.client == mock_client

    @pytest.mark.parametrize(
        "stock_id,year",
        [
            ("2330", 113),
            ("2412", 112),
            ("0050", 111),
        ],
    )
    def test_fetcher_accepts_valid_parameters(self, stock_id, year):
        """Test that fetcher accepts valid parameters."""
        fetcher = DividendFetcher()
        assert fetcher is not None
        assert isinstance(stock_id, str)
        assert isinstance(year, int)

    @pytest.mark.asyncio
    async def test_fetcher_async_method_exists(self):
        """Test that async methods exist."""
        fetcher = DividendFetcher()
        assert callable(fetcher.get_dividends_async)

    def test_dividend_fetcher_error(self):
        """Test that DividendFetcherError exists."""
        assert DividendFetcherError is not None
        with pytest.raises(DividendFetcherError):
            raise DividendFetcherError("test error")


class TestDividendParsing:
    """Test DividendFetcher parsing helper methods."""

    def test_extract_year_valid(self):
        """Test extracting year from text."""
        fetcher = DividendFetcher()
        assert fetcher._extract_year("113年第1季") == 113
        assert fetcher._extract_year("112年全年") == 112

    def test_extract_year_no_match(self):
        """Test year extraction with no match."""
        fetcher = DividendFetcher()
        assert fetcher._extract_year("N/A") is None
        assert fetcher._extract_year("") is None

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("期間:01/01-03/31", 1),
            ("期間:04/01-06/30", 2),
            ("期間:07/01-09/30", 3),
            ("期間:10/01-12/31", 4),
        ],
    )
    def test_extract_quarter(self, text, expected):
        """Test extracting quarter from date range."""
        fetcher = DividendFetcher()
        assert fetcher._extract_quarter(text) == expected

    def test_extract_quarter_none(self):
        """Test quarter extraction with no match."""
        fetcher = DividendFetcher()
        assert fetcher._extract_quarter("N/A") is None

    def test_parse_dividend_records_basic(self):
        """Test parsing dividend records from DataFrame."""
        fetcher = DividendFetcher()
        df = pd.DataFrame(
            [
                [
                    "股利所屬期間",
                    "普通股",
                    "持股者",
                    "",
                    "",
                    "",
                    "現金股利",
                    "股票股利",
                ],
                ["2024-01-01至03-31", "113年", "", "", "", "", "2.00", "1.50"],
            ],
            columns=[0, 1, 2, 3, 4, 5, 6, 7],
        )

        records = fetcher._parse_dividend_records([df], "2330", "台積電")
        assert len(records) > 0
        if records:
            assert records[0].stock_id == "2330"
            assert records[0].company_name == "台積電"

    def test_parse_dividend_records_skips_headers(self):
        """Test that header rows are skipped."""
        fetcher = DividendFetcher()
        df = pd.DataFrame(
            [
                [
                    "股利所屬期間",
                    "普通股",
                    "持股者",
                    "",
                    "",
                    "",
                    "現金股利",
                    "股票股利",
                ],
                ["期間", "年度", "類別", "", "", "", "金額", "數量"],
            ],
            columns=[0, 1, 2, 3, 4, 5, 6, 7],
        )

        records = fetcher._parse_dividend_records([df], "2330", "台積電")
        assert records == []

    def test_get_dividends_year_end_defaults(self):
        """Test that year_end defaults to year_start."""
        fetcher = DividendFetcher()
        mock_client = Mock()
        fetcher.client = mock_client
        mock_client.fetch_html_table.return_value = [
            pd.DataFrame([["2330 台積電"]], columns=[0])
        ]

        fetcher.get_dividends("2330", year_start=113)
        call_args = mock_client.fetch_html_table.call_args[0][1]
        assert call_args["date2"] == 113


class TestDividendEndToEnd:
    """Test DividendFetcher end-to-end methods."""

    def test_get_dividends_sync(self):
        """Test synchronous dividend fetching."""
        fetcher = DividendFetcher()
        mock_client = Mock()
        fetcher.client = mock_client

        dfs = [pd.DataFrame([["2330 台積電"]], columns=[0])]
        mock_client.fetch_html_table.return_value = dfs

        response = fetcher.get_dividends("2330", year_start=113, year_end=113)
        assert response.stock_id == "2330"
        assert response.year_start == 113
        assert response.year_end == 113

    @pytest.mark.asyncio
    async def test_get_dividends_async(self):
        """Test asynchronous dividend fetching."""
        fetcher = DividendFetcher()
        mock_client = AsyncMock()
        fetcher.client = mock_client

        dfs = [pd.DataFrame([["2330 台積電"]], columns=[0])]
        mock_client.fetch_html_table_async.return_value = dfs

        response = await fetcher.get_dividends_async("2330", year_start=113)
        assert response.stock_id == "2330"

    def test_get_annual_summary(self):
        """Test annual dividend summary calculation."""
        fetcher = DividendFetcher()
        mock_client = Mock()
        fetcher.client = mock_client

        # Mock a response with 2 dividend records matching parser expectations
        # Parser skips rows where first col contains "股利"/"期間" or is empty
        df = pd.DataFrame(
            [
                ["股利所屬期間", "113年", "現金股利", "", "", "", "2.00", "1.50"],
                ["普通股", "113年第1季", "01/01-03/31", "", "", "", "2.00", "1.50"],
                ["普通股", "113年第2季", "04/01-06/30", "", "", "", "3.00", "0.50"],
            ],
            columns=[0, 1, 2, 3, 4, 5, 6, 7],
        )
        mock_client.fetch_html_table.return_value = [
            pd.DataFrame([["2330 台積電"]], columns=[0]),
            df,
        ]

        summary = fetcher.get_annual_summary("2330", year=113)
        assert summary.stock_id == "2330"
        assert summary.year == 113
        assert summary.total_cash_dividend == 5.0  # 2.00 + 3.00
        assert summary.total_stock_dividend == 2.0  # 1.50 + 0.50

    def test_get_dividends_not_found(self):
        """Test error handling for missing dividend data."""
        fetcher = DividendFetcher()
        mock_client = Mock()
        fetcher.client = mock_client
        mock_client.fetch_html_table.side_effect = MOPSDataNotFoundError("No data")

        with pytest.raises(DividendFetcherError, match="No dividend data"):
            fetcher.get_dividends("9999", year_start=113)

    def test_get_dividends_client_error(self):
        """Test error handling for client errors."""
        fetcher = DividendFetcher()
        mock_client = Mock()
        fetcher.client = mock_client

        class CustomError(MOPSHTMLClientError):
            def __init__(self):
                self.message = "Network error"

        mock_client.fetch_html_table.side_effect = CustomError()

        with pytest.raises(DividendFetcherError, match="Failed to fetch dividend"):
            fetcher.get_dividends("2330", year_start=113)
