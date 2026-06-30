from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RiskItem(BaseModel):
    category: str
    description: str
    severity: Literal["High", "Medium", "Low"]


class ExecutiveSummaryData(BaseModel):
    businessOverview: str = ""
    revenueAndProfit: str = ""
    keyHighlights: list[str] = Field(default_factory=list)
    managementOutlook: str = ""
    notableChanges: str = ""


class RiskAnalysisData(BaseModel):
    risks: list[RiskItem] = Field(default_factory=list)


class InsightResponse(BaseModel):
    status: Literal["ready", "generating", "unavailable", "error"]
    data: ExecutiveSummaryData | RiskAnalysisData | None = None
    generatedAt: datetime | None = None
    cached: bool = False
    error: str | None = None
