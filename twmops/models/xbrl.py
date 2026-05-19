"""
XBRL-related data models
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class CalculationArc(BaseModel):
    from_concept: str = Field(..., description="Parent concept ID")
    to_concept: str = Field(..., description="Child concept ID")
    weight: float = Field(..., description="Weight (+1.0 add / -1.0 subtract)")
    order: float = Field(0.0, description="Sort order")


class PresentationArc(BaseModel):
    from_concept: str = Field(..., description="Parent concept ID")
    to_concept: str = Field(..., description="Child concept ID")
    order: float = Field(0.0, description="Sort order")
    preferred_label: Optional[str] = Field(None)


class XBRLFact(BaseModel):
    concept: str = Field(..., description="Concept ID")
    value: Optional[str] = Field(None, description="Value as string")
    unit: Optional[str] = Field(None)
    context_ref: str = Field(..., description="Context reference")
    decimals: Optional[int] = Field(None)


class XBRLContext(BaseModel):
    context_id: str
    entity: str
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    instant: Optional[str] = None


class XBRLPackage(BaseModel):
    stock_id: str
    year: int
    quarter: int
    calculation_arcs: Dict[str, List[CalculationArc]] = Field(default_factory=dict)
    presentation_arcs: Dict[str, List[PresentationArc]] = Field(default_factory=dict)
    facts: List[XBRLFact] = Field(default_factory=list)
    contexts: Dict[str, XBRLContext] = Field(default_factory=dict)
    labels: Dict[str, str] = Field(default_factory=dict)
    labels_en: Dict[str, str] = Field(default_factory=dict)
