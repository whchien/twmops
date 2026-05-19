from typing import Optional, List
from pydantic import BaseModel


class MonthlyRevenue(BaseModel):
    stock_id: str
    company_name: str
    year: int                                     # ROC year (民國年)
    month: int
    revenue: Optional[int] = None                 # Current month revenue (thousands TWD)
    revenue_last_month: Optional[int] = None
    revenue_last_year: Optional[int] = None
    mom_change: Optional[float] = None            # Month-over-month change (%)
    yoy_change: Optional[float] = None            # Year-over-year change (%)
    accumulated_revenue: Optional[int] = None
    accumulated_last_year: Optional[int] = None
    accumulated_yoy_change: Optional[float] = None
    comment: Optional[str] = None


class MarketRevenueResponse(BaseModel):
    year: int
    month: int
    market: str
    count: int
    data: List[MonthlyRevenue]
