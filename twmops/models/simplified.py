"""
Simplified financial statement format (similar to FinMind/FinLab style)
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class SimplifiedFinancialItem(BaseModel):
    date: str = Field(..., description="Report date (YYYY-MM-DD)")
    stock_id: str
    type: str = Field(..., description="Concept name (e.g., 'Revenue', 'GrossProfit')")
    value: Optional[float] = None
    origin_name: str = Field(..., description="Original Chinese label")


class SimplifiedFinancialStatement(BaseModel):
    stock_id: str
    year: int  # ROC year (民國年)
    quarter: int
    report_date: str  # YYYY-MM-DD
    statement_type: str  # income_statement | balance_sheet | cash_flow
    items: List[SimplifiedFinancialItem]


INCOME_STATEMENT_MAPPING = {
    "Revenue": "Revenue",
    "OperatingRevenue": "Revenue",
    "CostOfGoodsSold": "CostOfGoodsSold",
    "CostOfSales": "CostOfGoodsSold",
    "GrossProfit": "GrossProfit",
    "GrossProfitLoss": "GrossProfit",
    "GrossProfitLossFromOperations": "GrossProfit",
    "OperatingExpenses": "OperatingExpenses",
    "SellingExpenses": "SellingExpenses",
    "AdministrativeExpenses": "AdministrativeExpenses",
    "ResearchAndDevelopmentExpense": "ResearchAndDevelopmentExpense",
    "OperatingIncome": "OperatingIncome",
    "OperatingIncomeLoss": "OperatingIncome",
    "ProfitLossFromOperatingActivities": "OperatingIncome",
    "NonoperatingIncomeAndExpenses": "NonOperatingIncome",
    "OtherIncome": "OtherIncome",
    "OtherGainsAndLosses": "OtherGainsAndLosses",
    "FinanceCosts": "FinanceCosts",
    "InterestExpense": "InterestExpense",
    "ProfitLossBeforeTax": "ProfitBeforeTax",
    "IncomeTaxExpense": "IncomeTaxExpense",
    "ProfitLoss": "NetIncome",
    "ProfitLossAttributableToOwnersOfParent": "NetIncomeAttributableToOwners",
    "BasicEarningsPerShare": "EPS",
}

BALANCE_SHEET_MAPPING = {
    "Assets": "TotalAssets",
    "CurrentAssets": "CurrentAssets",
    "NoncurrentAssets": "NoncurrentAssets",
    "CashAndCashEquivalents": "Cash",
    "AccountsReceivable": "AccountsReceivable",
    "AccountsReceivableNet": "AccountsReceivable",
    "Inventories": "Inventory",
    "PropertyPlantAndEquipment": "PPE",
    "IntangibleAssets": "IntangibleAssets",
    "Liabilities": "TotalLiabilities",
    "CurrentLiabilities": "CurrentLiabilities",
    "NoncurrentLiabilities": "NoncurrentLiabilities",
    "ShortTermBorrowings": "ShortTermDebt",
    "LongTermBorrowings": "LongTermDebt",
    "AccountsPayable": "AccountsPayable",
    "Equity": "TotalEquity",
    "EquityAttributableToOwnersOfParent": "EquityAttributableToOwners",
    "Share": "ShareCapital",
    "CapitalSurplus": "CapitalSurplus",
    "RetainedEarnings": "RetainedEarnings",
}

CASH_FLOW_MAPPING = {
    "CashFlowsFromUsedInOperatingActivities": "OperatingCashFlow",
    "ProfitLossBeforeTax": "ProfitBeforeTax",
    "CashFlowsFromUsedInInvestingActivities": "InvestingCashFlow",
    "PaymentsToAcquirePropertyPlantAndEquipment": "CapitalExpenditure",
    "CashFlowsFromUsedInFinancingActivities": "FinancingCashFlow",
    "DividendsPaid": "DividendsPaid",
    "IncreaseDecreaseInCashAndCashEquivalents": "NetCashChange",
}


def get_statement_mapping(statement_type: str) -> dict:
    if statement_type == "income_statement":
        return INCOME_STATEMENT_MAPPING
    elif statement_type == "balance_sheet":
        return BALANCE_SHEET_MAPPING
    elif statement_type == "cash_flow":
        return CASH_FLOW_MAPPING
    return {}
