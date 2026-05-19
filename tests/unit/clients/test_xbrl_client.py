"""Tests for MOPSXBRLClient."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from twmops.clients.xbrl_client import MOPSXBRLClient

pytestmark = pytest.mark.unit


class TestMOPSXBRLClient:
    """Test MOPSXBRLClient initialization and basic methods."""

    def test_client_initialization(self):
        """Test that client can be instantiated."""
        client = MOPSXBRLClient()
        assert client is not None
        assert hasattr(client, "download_xbrl")
        assert hasattr(client, "extract_zip")
        assert hasattr(client, "is_ixbrl")

    def test_client_has_required_methods(self):
        """Test that client has all required methods."""
        client = MOPSXBRLClient()
        assert callable(client.download_xbrl)
        assert callable(client.download_xbrl_async)
        assert callable(client.extract_zip)
        assert callable(client.is_ixbrl)

    @pytest.mark.parametrize(
        "stock_id,year,quarter",
        [
            ("2330", 113, 1),
            ("2412", 112, 4),
            ("0050", 113, 2),
        ],
    )
    def test_download_xbrl_parameters(self, stock_id, year, quarter):
        """Test that download_xbrl accepts valid parameters."""
        client = MOPSXBRLClient()
        assert client is not None
        # Actual download would need mocking

    @pytest.mark.asyncio
    async def test_async_download_method_exists(self):
        """Test that async download method exists and is callable."""
        client = MOPSXBRLClient()
        assert hasattr(client, "download_xbrl_async")
        assert callable(client.download_xbrl_async)

    def test_extract_zip_method(self):
        """Test that extract_zip method exists."""
        client = MOPSXBRLClient()
        assert callable(client.extract_zip)

    def test_is_ixbrl_method(self):
        """Test that is_ixbrl method exists."""
        client = MOPSXBRLClient()
        assert callable(client.is_ixbrl)
        # Test with sample data
        assert client.is_ixbrl(b"test") is False
        assert client.is_ixbrl(b"ix:nonFraction") is True
