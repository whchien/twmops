"""
Financial statement data models
"""

from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class FinancialItem(BaseModel):
    account_code: str = Field(..., description="Account code")
    account_name: str = Field(..., description="Account name (Chinese)")
    account_name_en: Optional[str] = Field(None, description="Account name (English)")
    value: Optional[Decimal] = Field(None)
    weight: float = Field(
        1.0, description="Contribution weight to parent (+1.0 / -1.0)"
    )
    level: int = Field(0, description="Hierarchy depth (0 = top level)")
    children: List["FinancialItem"] = Field(default_factory=list)


class FinancialStatement(BaseModel):
    stock_id: str
    company_name: Optional[str] = None
    year: int = Field(..., description="ROC year (民國年)")
    quarter: Optional[int] = Field(None, ge=1, le=4)
    report_type: str = Field(
        ...,
        description="balance_sheet | income_statement | cash_flow | equity_statement",
    )
    is_standalone: bool = Field(False)
    items: List[FinancialItem] = Field(default_factory=list)
    currency: str = Field("TWD")
    unit: str = Field("thousands")
