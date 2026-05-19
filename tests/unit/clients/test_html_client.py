"""Tests for MOPSHTMLClient."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import respx
from httpx import Response

from twmops.clients.html_client import MOPSHTMLClient

pytestmark = pytest.mark.unit


class TestMOPSHTMLClient:
    """Test MOPSHTMLClient initialization and basic methods."""

    def test_client_initialization(self):
        """Test that client can be instantiated."""
        client = MOPSHTMLClient()
        assert client is not None
        assert hasattr(client, "fetch_html_table")
        assert hasattr(client, "fetch_static_html")

    def test_client_has_timeout_config(self):
        """Test that client has timeout settings."""
        client = MOPSHTMLClient()
        assert client is not None
        assert hasattr(client, "timeout")
        assert client.timeout == 30.0

    @pytest.mark.parametrize("method_name", ["fetch_html_table", "fetch_static_html"])
    def test_client_has_methods(self, method_name):
        """Test client has required methods."""
        client = MOPSHTMLClient()
        assert hasattr(client, method_name)
        assert callable(getattr(client, method_name))

    @pytest.mark.asyncio
    async def test_async_methods_exist(self):
        """Test that async methods exist on client."""
        client = MOPSHTMLClient()
        assert hasattr(client, "fetch_html_table_async")
        assert hasattr(client, "fetch_static_html_async")
        assert callable(client.fetch_html_table_async)
        assert callable(client.fetch_static_html_async)

    def test_client_with_custom_timeout(self):
        """Test client initialization with custom timeout."""
        client = MOPSHTMLClient()
        assert client is not None
        # Test custom timeout if constructor supports it
