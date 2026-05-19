"""Tests for RevenueFetcher."""

import pytest
import respx
from httpx import Response
import sys
from pathlib import Path

# Add tests directory to path to import conftest helpers
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import build_revenue_html, make_response
from twmops.fetchers.revenue import RevenueFetcher

pytestmark = pytest.mark.unit


class TestRevenueFetcher:
    """Test RevenueFetcher sync and async methods."""

    def test_get_market_revenue_sync(self, respx_mock):
        """Test synchronous market revenue fetching."""
        fetcher = RevenueFetcher()
        url = "https://mopsov.twse.com.tw/nas/t21/sii/t21sc03_113_3_0.html"

        html_content = build_revenue_html(
            [
                {
                    "stock_id": "2330",
                    "company_name": "台積電",
                    "revenue": "500000",
                    "revenue_last_month": "480000",
                    "revenue_last_year": "510000",
                    "mom_change": "4.17",
                    "yoy_change": "-1.96",
                }
            ]
        )
        respx_mock.get(url).mock(return_value=make_response(html_content))

        revenues = fetcher.get_market_revenue(year=113, month=3, market="sii")
        assert len(revenues) > 0
        assert revenues[0].stock_id == "2330"
        assert revenues[0].company_name == "台積電"

    @pytest.mark.asyncio
    async def test_get_market_revenue_async(self, respx_mock):
        """Test asynchronous market revenue fetching."""
        fetcher = RevenueFetcher()
        url = "https://mopsov.twse.com.tw/nas/t21/sii/t21sc03_113_3_0.html"

        respx_mock.get(url).mock(
            return_value=make_response(
                build_revenue_html(
                    [
                        {
                            "stock_id": "2330",
                            "company_name": "台積電",
                            "revenue": "500000",
                        }
                    ]
                )
            )
        )

        revenues = await fetcher.get_market_revenue_async(
            year=113, month=3, market="sii"
        )
        assert len(revenues) > 0
        assert revenues[0].stock_id == "2330"

    def test_get_single_revenue_sync(self, respx_mock):
        """Test fetching single company revenue."""
        fetcher = RevenueFetcher()
        url = "https://mopsov.twse.com.tw/nas/t21/sii/t21sc03_113_3_0.html"

        respx_mock.get(url).mock(
            return_value=make_response(
                build_revenue_html(
                    [
                        {
                            "stock_id": "2330",
                            "company_name": "台積電",
                            "revenue": "500000",
                        },
                        {
                            "stock_id": "2454",
                            "company_name": "聯發科",
                            "revenue": "300000",
                        },
                    ]
                )
            )
        )

        rev = fetcher.get_single_revenue("2330", year=113, month=3, market="sii")
        assert rev is not None
        assert rev.stock_id == "2330"
        assert rev.company_name == "台積電"

    def test_get_single_revenue_not_found(self, respx_mock):
        """Test when single company not found."""
        fetcher = RevenueFetcher()
        url = "https://mopsov.twse.com.tw/nas/t21/sii/t21sc03_113_3_0.html"

        respx_mock.get(url).mock(
            return_value=make_response(
                build_revenue_html(
                    [
                        {
                            "stock_id": "2330",
                            "company_name": "台積電",
                            "revenue": "500000",
                        }
                    ]
                )
            )
        )

        rev = fetcher.get_single_revenue("9999", year=113, month=3, market="sii")
        assert rev is None

    def test_invalid_market(self):
        """Test validation of market type."""
        fetcher = RevenueFetcher()
        with pytest.raises(Exception):  # RevenueFetcherError
            fetcher.get_market_revenue(year=113, month=3, market="invalid")

    def test_get_market_revenue_404(self, respx_mock):
        """Test handling of 404 error."""
        from twmops.fetchers.revenue import RevenueFetcherError

        fetcher = RevenueFetcher()
        url = "https://mopsov.twse.com.tw/nas/t21/sii/t21sc03_113_3_0.html"

        respx_mock.get(url).mock(return_value=Response(404, text="Not Found"))

        with pytest.raises(RevenueFetcherError):
            fetcher.get_market_revenue(year=113, month=3, market="sii")

    def test_different_markets(self, respx_mock):
        """Test different market types."""
        fetcher = RevenueFetcher()

        for market in ["sii", "otc", "rotc", "pub"]:
            url = f"https://mopsov.twse.com.tw/nas/t21/{market}/t21sc03_113_3_0.html"
            respx_mock.get(url).mock(
                return_value=make_response(
                    build_revenue_html([{"stock_id": "2330", "company_name": "台積電"}])
                )
            )
            revenues = fetcher.get_market_revenue(year=113, month=3, market=market)
            assert len(revenues) > 0

    def test_multiple_records(self, respx_mock):
        """Test parsing multiple revenue records."""
        fetcher = RevenueFetcher()
        url = "https://mopsov.twse.com.tw/nas/t21/sii/t21sc03_113_3_0.html"

        respx_mock.get(url).mock(
            return_value=make_response(
                build_revenue_html(
                    [
                        {
                            "stock_id": "2330",
                            "company_name": "台積電",
                            "revenue": "500000",
                        },
                        {
                            "stock_id": "2454",
                            "company_name": "聯發科",
                            "revenue": "300000",
                        },
                        {
                            "stock_id": "2317",
                            "company_name": "鴻海",
                            "revenue": "400000",
                        },
                    ]
                )
            )
        )

        revenues = fetcher.get_market_revenue(year=113, month=3, market="sii")
        assert len(revenues) >= 3
        stock_ids = [r.stock_id for r in revenues]
        assert "2330" in stock_ids
        assert "2454" in stock_ids
        assert "2317" in stock_ids
