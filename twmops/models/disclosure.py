from typing import Optional, List
from pydantic import BaseModel


class FundsLending(BaseModel):
    entity: str
    has_balance: bool
    current_month: Optional[int] = None   # thousands TWD
    previous_month: Optional[int] = None
    max_limit: Optional[int] = None


class EndorsementGuarantee(BaseModel):
    entity: str
    has_balance: bool
    monthly_change: Optional[int] = None
    accumulated_balance: Optional[int] = None
    max_limit: Optional[int] = None


class CrossCompanyGuarantee(BaseModel):
    parent_to_subsidiary: Optional[int] = None
    subsidiary_to_parent: Optional[int] = None


class ChinaGuarantee(BaseModel):
    entity: str
    has_balance: bool
    monthly_change: Optional[int] = None
    accumulated_balance: Optional[int] = None


class DisclosureResponse(BaseModel):
    stock_id: str
    company_name: str
    year: int
    month: int
    funds_lending: List[FundsLending] = []
    endorsement_guarantee: List[EndorsementGuarantee] = []
    cross_company: Optional[CrossCompanyGuarantee] = None
    china_guarantee: List[ChinaGuarantee] = []
