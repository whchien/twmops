from typing import Optional, List
from pydantic import BaseModel


class DividendRecord(BaseModel):
    stock_id: str
    company_name: str
    year: int                              # ROC year (民國年)
    quarter: Optional[int] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    board_resolution_date: Optional[str] = None
    cash_dividend: Optional[float] = None  # Per share (TWD)
    stock_dividend: Optional[float] = None
    total_dividend: Optional[float] = None
    ex_dividend_date: Optional[str] = None
    ex_rights_date: Optional[str] = None


class DividendSummary(BaseModel):
    stock_id: str
    company_name: str
    year: int
    total_cash_dividend: float = 0.0
    total_stock_dividend: float = 0.0
    total_dividend: float = 0.0
    quarterly_dividends: List[DividendRecord] = []


class DividendResponse(BaseModel):
    stock_id: str
    company_name: str
    year_start: int
    year_end: int
    count: int
    records: List[DividendRecord]
