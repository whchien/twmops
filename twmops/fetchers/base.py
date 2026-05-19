"""
BaseFetcher — Abstract base class for all MOPS fetchers.
Defines common patterns for sync/async dual-mode fetching.
"""

from abc import ABC, abstractmethod
from typing import Optional, Type

from twmops.clients.html_client import (
    MOPSHTMLClient,
    MOPSHTMLClientError,
    MOPSDataNotFoundError,
)


class BaseFetcherError(Exception):
    """Base exception for all fetcher errors."""

    pass


class BaseFetcher(ABC):
    """
    Abstract base class for HTML-based fetchers.

    Provides:
    - Common __init__ pattern (html_client injection)
    - Unified error handling via _handle_error()
    - Type hints for error classes

    Subclasses should implement:
    - Public sync/async methods (e.g., get_x(), get_x_async())
    - Private param builders (e.g., _get_params())
    - Private response parsers (e.g., _parse_response())
    """

    error_class: Type[BaseFetcherError] = BaseFetcherError

    def __init__(self, html_client: Optional[MOPSHTMLClient] = None):
        self.client = html_client or MOPSHTMLClient()

    def _handle_error(self, e: MOPSHTMLClientError, context: str) -> None:
        """
        Handle MOPSHTMLClient errors uniformly.

        Args:
            e: The exception from MOPSHTMLClient
            context: Error context message (e.g., "No revenue data for {year}/{month}")

        Raises:
            self.error_class with appropriate message
        """
        if isinstance(e, MOPSDataNotFoundError):
            raise self.error_class(context)
        raise self.error_class(f"Failed to fetch data: {e.message}")

    @classmethod
    @abstractmethod
    def endpoint(cls) -> str:
        """Return the MOPS endpoint name (e.g., 'ajax_t05st11')."""
        pass


class AjaxFetcher(BaseFetcher):
    """
    Base class for AJAX-based fetchers (POST to MOPS endpoints).
    Implements common pattern for fetch_html_table / fetch_html_table_sync.
    """

    pass


class StaticHtmlFetcher(BaseFetcher):
    """
    Base class for static HTML fetchers (GET from MOPS URLs).
    Implements common pattern for fetch_static_html / fetch_static_html_sync.
    """

    pass
