"""Shared pytest fixtures and utilities for twmops tests."""
import pytest
import respx
from httpx import Response


@pytest.fixture
def respx_mock():
    """Provide respx mock router for all tests."""
    with respx.mock:
        yield respx


def make_response(html_bytes, status_code=200):
    """Create an HTTP Response from Big5-encoded HTML bytes.

    Args:
        html_bytes: Bytes content (from build_*_html functions)
        status_code: HTTP status code

    Returns:
        httpx.Response object with proper encoding
    """
    return Response(status_code, content=html_bytes, headers={"content-type": "text/html; charset=big5"})


def build_html_table(rows, encoding="big5"):
    """Build HTML with a simple table for testing.

    Args:
        rows: List of lists, where each inner list is a table row
        encoding: Encoding to use (default: big5)

    Returns:
        HTML bytes encoded with the specified encoding
    """
    html = "<html><body><table>\n"
    for row in rows:
        html += "  <tr>\n"
        for cell in row:
            html += f"    <td>{cell}</td>\n"
        html += "  </tr>\n"
    html += "</table></body></html>"
    # Encode as bytes for the mock response
    return html.encode(encoding)


def build_revenue_html(records):
    """Build revenue table HTML.

    Args:
        records: List of dicts with keys: stock_id, company_name, revenue, revenue_last_month,
                revenue_last_year, mom_change, yoy_change, accumulated_revenue,
                accumulated_last_year, accumulated_yoy_change, comment
    """
    rows = [
        [
            "公司代號",
            "公司名稱",
            "當月營收",
            "上月營收",
            "去年同月營收",
            "上月比較%",
            "去年同月比較%",
            "累計營收",
            "去年累計營收",
            "累計比較%",
            "備註",
        ]
    ]

    for rec in records:
        rows.append([
            rec.get("stock_id", "2330"),
            rec.get("company_name", "台積電"),
            rec.get("revenue", "500000"),
            rec.get("revenue_last_month", "480000"),
            rec.get("revenue_last_year", "510000"),
            rec.get("mom_change", "4.17"),
            rec.get("yoy_change", "-1.96"),
            rec.get("accumulated_revenue", "1500000"),
            rec.get("accumulated_last_year", "1530000"),
            rec.get("accumulated_yoy_change", "-1.96"),
            rec.get("comment", "-"),
        ])

    return build_html_table(rows)


def build_disclosure_html(records):
    """Build disclosure data table HTML."""
    rows = [["公司代號", "公司名稱", "資金貸與", "背書保證", "跨公司保證", "中國擔保", "其他"]]
    for rec in records:
        rows.append([
            rec.get("stock_id", "2330"),
            rec.get("company_name", "台積電"),
            rec.get("funds_lending", "0"),
            rec.get("endorsement", "0"),
            rec.get("cross_company", "0"),
            rec.get("china_guarantee", "0"),
            rec.get("other", "-"),
        ])
    return build_html_table(rows)


def build_dividend_html(records):
    """Build dividend table HTML."""
    rows = [["公司代號", "公司名稱", "年度", "除息日", "股利", "現金股利", "備註"]]
    for rec in records:
        rows.append([
            rec.get("stock_id", "2330"),
            rec.get("company_name", "台積電"),
            rec.get("year", "113"),
            rec.get("ex_date", "2024-05-15"),
            rec.get("dividend", "8.00"),
            rec.get("cash_dividend", "8.00"),
            rec.get("comment", "-"),
        ])
    return build_html_table(rows)


def build_insider_pledging_html(records):
    """Build insider share pledging table HTML."""
    rows = [["公司代號", "公司名稱", "董監持股", "其他", "合計"]]
    for rec in records:
        rows.append([
            rec.get("stock_id", "2330"),
            rec.get("company_name", "台積電"),
            rec.get("director_share", "100"),
            rec.get("other", "50"),
            rec.get("total", "150"),
        ])
    return build_html_table(rows)
