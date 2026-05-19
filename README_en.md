# twmops: Taiwan MOPS Financial Data Python Package

Fetch Taiwan MOPS (Market Observation Post System) financial data with Python. Access revenue, financial statements, dividends, disclosure, and insider trading data.

## Installation

```bash
pip install twmops
```

For full XBRL parsing support (recommended):
```bash
pip install 'twmops[xbrl]'
```

## Quick Start

```python
from twmops import RevenueFetcher, FinancialFetcher, DividendFetcher

# Monthly revenue
rev_fetcher = RevenueFetcher()
tsmc = rev_fetcher.get_single_revenue("2330", year=113, month=3)
print(f"{tsmc.company_name}: NT${tsmc.revenue:,} thousand")

# Financial statements
fin_fetcher = FinancialFetcher()
stmt = fin_fetcher.get_financial_statement(
    stock_id="2330", year=113, quarter=3,
    report_type="balance_sheet", format="tree"
)

# Dividends
div_fetcher = DividendFetcher()
dividends = div_fetcher.get_dividends("2330", year_start=111, year_end=113)
```

## Features

- **RevenueFetcher** — Monthly revenue for single companies or market-wide
- **FinancialFetcher** — Balance sheet, income statement, cash flow, equity statements (hierarchical or flat format)
- **DividendFetcher** — Historical dividend records and annual summaries
- **DisclosureFetcher** — Related-party transactions, funds lending, endorsements
- **InsidersFetcher** — Director/supervisor share pledging details
- **Async support** — All methods available with `_async` suffix for concurrent requests

## API Reference

### RevenueFetcher
```python
get_market_revenue(year, month, market="sii", company_type=0) → list[MonthlyRevenue]
get_single_revenue(stock_id, year, month, market="sii") → MonthlyRevenue
```

### FinancialFetcher
```python
get_financial_statement(stock_id, year, quarter, report_type, format="tree") → FinancialStatement
get_simplified_statement(stock_id, year, quarter, statement_type) → SimplifiedFinancialStatement
```

### DividendFetcher
```python
get_dividends(stock_id, year_start, year_end) → DividendResponse
get_annual_summary(stock_id, year) → DividendSummary
```

### DisclosureFetcher
```python
get_disclosure(stock_id, year=None, month=None, market="sii") → DisclosureResponse
```

### InsidersFetcher
```python
get_share_pledging(stock_id, year=None, month=None, market="sii") → PledgingResponse
```

**Async versions**: Append `_async` to any method name for async support.

## Data Formats

### Year and Month
Taiwan uses **ROC year** (民國年): ROC year 113 = Western year 2024 (113 + 1911)

### Markets
- `sii`: 上市 (TWSE listed)
- `otc`: 上櫃 (OTC)
- `rotc`: 興櫃 (Emerging)
- `pub`: 公開發行 (Public)

### Units
All amounts in thousands of TWD. Percentages as decimals (0.05 = 5%).

## Examples

See `notebooks/` for comprehensive examples:
- `00_quickstart.ipynb` — Get started in 5 minutes
- `01_revenue.ipynb` — Revenue analysis
- `02_financial_statements.ipynb` — Financial statement usage
- `03_insider_pledging.ipynb` — Share pledging analysis
- `04_disclosure.ipynb` — Related-party transactions
- `05_advanced_examples.ipynb` — Multi-source analysis

## Notes

### Rate Limiting
The HTML client enforces 1 request/second to respect MOPS limits.

### XBRL Parsing
- **With Arelle** (`pip install 'twmops[xbrl]'`): Full XBRL support
- **Without Arelle** (lxml fallback): Basic parsing only
- First XBRL download: ~1-2 seconds (taxonomy cache), subsequent: <1 second

### Async Usage
```python
import asyncio

async def fetch_all():
    revenue, stmt, dividends = await asyncio.gather(
        rev_fetcher.get_market_revenue_async(year=113, month=3, market="sii"),
        fin_fetcher.get_financial_statement_async(stock_id="2330", year=113, quarter=3),
        div_fetcher.get_dividends_async(stock_id="2330", year_start=110, year_end=113),
    )
    return revenue, stmt, dividends

asyncio.run(fetch_all())
```

## Troubleshooting

**SSL Certificate Error** — If you see `certificate verify failed`, update SSL certificates:
```bash
pip install --upgrade certifi
```
The package automatically retries without verification if SSL fails (you may see a warning).

**Missing `arelle` module** — This is expected without `pip install 'twmops[xbrl]'`. The package falls back to lxml parsing with reduced functionality.

**`MOPSDataNotFoundError`** — The requested data is unavailable. This happens for very recent companies, delisted companies, or non-existent stock IDs.

**Network timeout** — If MOPS is slow, try retrying with exponential backoff or check [MOPS status](https://mops.twse.com.tw). Consider using a VPN if outside Taiwan.

## Development

```bash
git clone <repo>
cd tw-mops
pip install -e '.[xbrl]'
pytest tests/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## Legal Notice

**Data Source**: This package fetches data from Taiwan's MOPS, maintained by TWSE and Taiwan OTC Exchange.

**Terms of Use**: Users are responsible for complying with MOPS's [terms of use](https://mops.twse.com.tw). MOPS data is public, but usage restrictions may apply based on jurisdiction and use case. For commercial use, investment funds, or data redistribution, review MOPS's official terms.

**Disclaimer**: This package is provided "as-is" without warranty. Always validate fetched data independently before making investment decisions.

## License

MIT License. See [LICENSE](LICENSE) for details. The license covers only this package's source code, not the data fetched from MOPS.

## Citation

```bibtex
@software{twmops,
  title = {twmops: Taiwan MOPS Financial Data Python Package},
  author = {You},
  year = {2024},
  url = {https://github.com/...}
}
```

## Support

- **Issues & Feature Requests**: [GitHub Issues](https://github.com/...)
- **MOPS Official**: https://mops.twse.com.tw
