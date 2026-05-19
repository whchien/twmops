"""
twmops — Taiwan MOPS (公開資訊觀測站) Python client

Fetch financial data from Taiwan's Market Observation Post System:
- Monthly revenue
- XBRL financial statements (balance sheet, income statement, cash flow, equity)
- Insider share pledging
- Dividend records
- Disclosure (funds lending, endorsement/guarantee)

Usage:
    from twmops import RevenueFetcher

    fetcher = RevenueFetcher()
    tsmc = fetcher.get_single_revenue("2330", year=113, month=3)
    print(f"{tsmc.company_name}: NT${tsmc.revenue:,} thousand")
"""

from twmops.fetchers.financial import FinancialFetcher
from twmops.fetchers.revenue import RevenueFetcher
from twmops.fetchers.disclosure import DisclosureFetcher
from twmops.fetchers.dividend import DividendFetcher
from twmops.fetchers.insiders import InsidersFetcher

__all__ = [
    "FinancialFetcher",
    "RevenueFetcher",
    "DisclosureFetcher",
    "DividendFetcher",
    "InsidersFetcher",
]
