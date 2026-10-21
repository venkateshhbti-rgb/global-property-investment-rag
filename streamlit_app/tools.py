"""Deterministic property maths. The LLM never calculates; these functions do."""
from typing import Dict, Optional


def mortgage_payment(principal: float, annual_rate_pct: float, years: int) -> float:
    """Monthly payment of a standard amortising loan."""
    if principal < 0 or years <= 0 or annual_rate_pct < 0:
        raise ValueError("principal and rate must be >= 0 and years > 0")
    months = years * 12
    if principal == 0:
        return 0.0
    monthly_rate = annual_rate_pct / 100 / 12
    if monthly_rate == 0:
        return principal / months
    return principal * monthly_rate / (1 - (1 + monthly_rate) ** -months)


def calc_yield(
    price: float,
    monthly_rent: float,
    vacancy_pct: float = 5.0,
    service_charges: float = 0.0,
    maintenance: float = 0.0,
    property_tax: float = 0.0,
    management_pct: float = 0.0,
    purchase_cost_pct: float = 0.0,
    loan_pct: float = 0.0,
    interest_rate_pct: float = 0.0,
    loan_years: int = 25,
) -> Dict[str, Optional[float]]:
    """Gross and net rental yield, cash flow and (optionally) cash-on-cash return.

    service_charges, maintenance and property_tax are yearly amounts. management_pct is a share of collected rent.
    purchase_cost_pct covers one-off costs such as transfer fees and agent commission, as a share of price.
    """
    if price <= 0:
        raise ValueError("price must be > 0")
    if monthly_rent < 0 or min(service_charges, maintenance, property_tax) < 0:
        raise ValueError("rent and yearly costs must be >= 0")
    for name, value in (("vacancy_pct", vacancy_pct), ("management_pct", management_pct), ("loan_pct", loan_pct)):
        if not 0 <= value <= 100:
            raise ValueError(f"{name} must be between 0 and 100")
    if purchase_cost_pct < 0 or interest_rate_pct < 0:
        raise ValueError("purchase_cost_pct and interest_rate_pct must be >= 0")

    gross_rent = monthly_rent * 12
    collected_rent = gross_rent * (1 - vacancy_pct / 100)
    management = collected_rent * management_pct / 100
    operating_costs = service_charges + maintenance + property_tax + management
    net_income = collected_rent - operating_costs

    total_cost = price * (1 + purchase_cost_pct / 100)
    loan = price * loan_pct / 100
    equity = total_cost - loan
    annual_debt_service = mortgage_payment(loan, interest_rate_pct, loan_years) * 12 if loan > 0 else 0.0
    cash_flow = net_income - annual_debt_service

    return {
        "gross_yield_pct": round(gross_rent / price * 100, 2),
        "net_yield_pct": round(net_income / price * 100, 2),
        "net_yield_on_total_cost_pct": round(net_income / total_cost * 100, 2),
        "gross_annual_rent": round(gross_rent, 2),
        "collected_annual_rent": round(collected_rent, 2),
        "operating_costs": round(operating_costs, 2),
        "net_annual_income": round(net_income, 2),
        "total_purchase_cost": round(total_cost, 2),
        "loan_amount": round(loan, 2),
        "equity_invested": round(equity, 2),
        "monthly_mortgage_payment": round(annual_debt_service / 12, 2),
        "annual_cash_flow": round(cash_flow, 2),
        "cash_on_cash_pct": round(cash_flow / equity * 100, 2) if equity > 0 else None,
        "payback_years": round(total_cost / net_income, 1) if net_income > 0 else None,
    }
