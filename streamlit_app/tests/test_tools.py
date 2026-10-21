import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools import calc_yield, mortgage_payment  # noqa: E402


def test_gross_yield_is_annual_rent_over_price():
    r = calc_yield(price=500_000, monthly_rent=3_000, vacancy_pct=0)
    assert r["gross_yield_pct"] == 7.2          # 36,000 / 500,000
    assert r["net_yield_pct"] == 7.2            # no costs, no vacancy


def test_costs_vacancy_and_management_reduce_net_yield():
    r = calc_yield(price=500_000, monthly_rent=3_000, vacancy_pct=10, service_charges=6_000,
                   maintenance=2_000, property_tax=1_000, management_pct=5)
    collected = 36_000 * 0.9                    # 32,400
    management = collected * 0.05               # 1,620
    assert r["collected_annual_rent"] == collected
    assert r["operating_costs"] == 6_000 + 2_000 + 1_000 + management
    assert r["net_annual_income"] == collected - r["operating_costs"]
    assert r["net_yield_pct"] == round(r["net_annual_income"] / 500_000 * 100, 2)


def test_purchase_costs_lower_yield_on_total_cost():
    r = calc_yield(price=1_000_000, monthly_rent=5_000, vacancy_pct=0, purchase_cost_pct=4)
    assert r["total_purchase_cost"] == 1_040_000
    assert r["net_yield_on_total_cost_pct"] < r["net_yield_pct"]


def test_payback_years():
    r = calc_yield(price=400_000, monthly_rent=2_000, vacancy_pct=0)
    assert r["payback_years"] == round(400_000 / 24_000, 1)


def test_payback_is_none_when_income_not_positive():
    r = calc_yield(price=400_000, monthly_rent=500, vacancy_pct=0, service_charges=20_000)
    assert r["payback_years"] is None


def test_mortgage_known_value():
    # 200,000 at 6% over 30 years -> 1,199.10 per month
    assert math.isclose(mortgage_payment(200_000, 6, 30), 1199.10, abs_tol=0.01)


def test_zero_interest_mortgage_is_straight_division():
    assert mortgage_payment(120_000, 0, 10) == 1_000


def test_leveraged_cash_flow_and_cash_on_cash():
    r = calc_yield(price=500_000, monthly_rent=3_000, vacancy_pct=0, loan_pct=60, interest_rate_pct=5, loan_years=25)
    assert r["loan_amount"] == 300_000
    assert r["equity_invested"] == 200_000
    expected_payment = mortgage_payment(300_000, 5, 25)
    assert r["monthly_mortgage_payment"] == round(expected_payment, 2)
    assert r["annual_cash_flow"] == round(36_000 - expected_payment * 12, 2)
    assert r["cash_on_cash_pct"] == round(r["annual_cash_flow"] / 200_000 * 100, 2)


@pytest.mark.parametrize("kwargs", [
    {"price": 0, "monthly_rent": 1000},
    {"price": -5, "monthly_rent": 1000},
    {"price": 100_000, "monthly_rent": -1},
    {"price": 100_000, "monthly_rent": 1000, "vacancy_pct": 120},
    {"price": 100_000, "monthly_rent": 1000, "service_charges": -1},
    {"price": 100_000, "monthly_rent": 1000, "loan_pct": 101},
])
def test_invalid_inputs_raise(kwargs):
    with pytest.raises(ValueError):
        calc_yield(**kwargs)
