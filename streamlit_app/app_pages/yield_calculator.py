import streamlit as st

from tools import calc_yield

st.header("Yield calculator")
st.caption("Every number on this page is calculated by code, never by the AI.")

currency = st.text_input("Currency label", value="USD", max_chars=6)

left, right = st.columns(2)
with left:
    price = st.number_input("Purchase price", min_value=0.0, value=500_000.0, step=10_000.0)
    monthly_rent = st.number_input("Monthly rent", min_value=0.0, value=3_000.0, step=100.0)
    vacancy = st.slider("Vacancy (% of the year empty)", 0, 50, 5)
    purchase_costs = st.number_input("One-off purchase costs (% of price)", min_value=0.0, value=4.0, step=0.5)
with right:
    service = st.number_input("Service charges per year", min_value=0.0, value=6_000.0, step=500.0)
    maintenance = st.number_input("Maintenance per year", min_value=0.0, value=2_000.0, step=500.0)
    tax = st.number_input("Property tax per year", min_value=0.0, value=0.0, step=500.0)
    management = st.number_input("Management fee (% of collected rent)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)

with st.expander("Financing (optional)"):
    loan_pct = st.slider("Loan (% of price)", 0, 90, 0)
    rate = st.number_input("Interest rate (% per year)", min_value=0.0, value=5.0, step=0.25)
    years = st.number_input("Loan term (years)", min_value=1, value=25, step=1)

if price <= 0:
    st.warning("Enter a purchase price above zero.", icon=":material/warning:")
    st.stop()

r = calc_yield(price, monthly_rent, vacancy, service, maintenance, tax, management, purchase_costs, loan_pct, rate, int(years))

with st.container(horizontal=True):
    st.metric("Gross yield", f"{r['gross_yield_pct']}%", border=True)
    st.metric("Net yield", f"{r['net_yield_pct']}%", border=True)
    st.metric("Net yield on total cost", f"{r['net_yield_on_total_cost_pct']}%", border=True)
    st.metric("Payback", f"{r['payback_years']} years" if r["payback_years"] else "n/a", border=True)

st.write(f"Collected rent per year: **{r['collected_annual_rent']:,.0f} {currency}** · costs: **{r['operating_costs']:,.0f}** · "
         f"net income: **{r['net_annual_income']:,.0f}** · total purchase cost: **{r['total_purchase_cost']:,.0f}**")
if loan_pct:
    coc = f"{r['cash_on_cash_pct']}%" if r["cash_on_cash_pct"] is not None else "n/a"
    st.write(f"Loan: **{r['loan_amount']:,.0f}** · monthly payment: **{r['monthly_mortgage_payment']:,.0f}** · "
             f"annual cash flow: **{r['annual_cash_flow']:,.0f}** · cash-on-cash: **{coc}**")
