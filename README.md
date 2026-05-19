# twmops：台灣 MOPS 財務資料 Python 套件

用 Python 取得台灣公開資訊觀測站（MOPS / Market Observation Post System）的財務資料。支援營收、財務報表、股利、關聯揭露及內部人交易資料。

**語言** | [English](README_en.md)

## 安裝

```bash
pip install twmops
```

完整 XBRL 解析支援（推薦）：
```bash
pip install 'twmops[xbrl]'
```

## 快速開始

```python
from twmops import RevenueFetcher, FinancialFetcher, DividendFetcher

# 月營收
rev_fetcher = RevenueFetcher()
tsmc = rev_fetcher.get_single_revenue("2330", year=113, month=3)
print(f"{tsmc.company_name}: NT${tsmc.revenue:,} 千元")

# 財務報表
fin_fetcher = FinancialFetcher()
stmt = fin_fetcher.get_financial_statement(
    stock_id="2330", year=113, quarter=3,
    report_type="balance_sheet", format="tree"
)

# 股利
div_fetcher = DividendFetcher()
dividends = div_fetcher.get_dividends("2330", year_start=111, year_end=113)
```

## 功能

- **RevenueFetcher** — 單一公司或全市場月營收
- **FinancialFetcher** — 資產負債表、損益表、現金流量表、股東權益變動表（分層或平面格式）
- **DividendFetcher** — 歷史股利紀錄與年度彙總
- **DisclosureFetcher** — 關聯人交易、資金貸與、背書保證
- **InsidersFetcher** — 董監事股份質押詳情
- **非同步支援** — 所有方法提供 `_async` 後綴版本支援併行請求

## API 參考

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

**非同步版本**：在任何方法名稱加上 `_async` 後綴可使用非同步支援。

## 資料格式

### 年份與月份
台灣使用**民國年**：民國 113 年 = 西元 2024 年（113 + 1911）

### 市場代碼
- `sii`: 上市（TWSE 上市公司）
- `otc`: 上櫃（OTC）
- `rotc`: 興櫃（Emerging）
- `pub`: 公開發行（Public）

### 單位
所有金額單位為新台幣千元。百分比以小數表示（0.05 = 5%）。

## 範例

詳見 `notebooks/` 中的完整範例：
- `00_快速開始.ipynb` — 5 分鐘快速入門
- `01_營收.ipynb` — 營收分析
- `02_財務報表.ipynb` — 財務報表使用
- `03_內部人股份質押.ipynb` — 股份質押分析
- `04_關聯人揭露.ipynb` — 關聯人交易
- `05_進階範例.ipynb` — 多來源整合分析

## 注意事項

### 速率限制
HTML 客戶端強制每秒 1 個請求以尊重 MOPS 限制。

### XBRL 解析
- **搭配 Arelle**（`pip install 'twmops[xbrl]'`）：完整 XBRL 支援
- **無 Arelle**（lxml 備用）：基礎解析僅
- 首次 XBRL 下載：~1-2 秒（分類法快取），後續：<1 秒

### 非同步使用
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

## 疑難排解

**SSL 憑證錯誤** — 如出現 `certificate verify failed`，請更新 SSL 憑證：
```bash
pip install --upgrade certifi
```
套件在 SSL 失敗時會自動重試（可能看到警告訊息）。

**缺少 `arelle` 模組** — 未執行 `pip install 'twmops[xbrl]'` 時正常。套件會改用 lxml 解析並降低功能。

**`MOPSDataNotFoundError`** — 請求的資料無法取得。這會發生在全新上市公司、已下市公司或不存在的股票代號上。

**網路逾時** — 若 MOPS 緩慢，嘗試使用指數退避重試或檢查 [MOPS 狀態](https://mops.twse.com.tw)。若在台灣以外，考慮使用 VPN。

## 開發

```bash
git clone <repo>
cd tw-mops
pip install -e '.[xbrl]'
pytest tests/
```

詳見 [CONTRIBUTING.md](CONTRIBUTING.md) 貢獻指南。

## 法律聲明

**資料來源**：本套件從台灣 MOPS 取得資料，由 TWSE 及台灣櫃檯買賣中心維護。

**使用條款**：使用者必須遵守 MOPS 的[使用條款](https://mops.twse.com.tw)。MOPS 資料為公開資訊，但使用可能受管轄區與使用目的限制。商業使用、投資基金或資料重新分發，請檢視 MOPS 官方條款。

**免責聲明**：本套件以「現況」提供，不含任何保固。做投資決策前務必獨立驗證取得資料。

## 授權

MIT License。詳見 [LICENSE](LICENSE)。授權僅涵蓋本套件源碼，不包含從 MOPS 取得的資料。

## 引用

```bibtex
@software{twmops,
  title = {twmops: Taiwan MOPS Financial Data Python Package},
  author = {You},
  year = {2024},
  url = {https://github.com/...}
}
```

## 支援

- **議題與功能請求**：[GitHub Issues](https://github.com/...)
- **MOPS 官方**：https://mops.twse.com.tw
