import os

import streamlit as st

st.set_page_config(page_title="Property investment consultant", page_icon=":material/home_work:", layout="wide")

DISCLAIMER = ("Informational only, not financial, tax or legal advice. "
              "Figures come from the loaded documents and open data and may be out of date.")


def _load_secrets() -> None:
    """Copy plain-text secrets (.streamlit/secrets.toml or Streamlit Cloud) into the environment."""
    try:
        for key in st.secrets:
            value = st.secrets[key]
            if isinstance(value, str):
                os.environ.setdefault(key, value)
    except Exception:
        pass  # no secrets file: fall back to environment variables and backend/.env


_load_secrets()

import query  # noqa: E402  (must come before the backend modules: it sets their paths)
import services  # noqa: E402
from store import MIN_PASSWORD, store  # noqa: E402

st.session_state.setdefault("chat", [])
st.session_state.setdefault("compare_result", None)


@st.cache_resource(show_spinner="Loading documents and the search index (about a minute the first time)...")
def load_rag():
    rag = query.get_rag()
    services.prepare_providers()
    return rag


def signed_in_user():
    auth = st.session_state.get("auth")
    user = store.user_for_token(auth["token"]) if auth else None
    if auth and not user:
        st.session_state.pop("auth", None)
    return user


def login_view() -> None:
    _, middle, _ = st.columns([1, 2, 1])
    with middle:
        st.title("Property Investment Consultant")
        st.caption("Sign in to continue")
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary", icon=":material/login:")
        if submitted:
            result = store.login(username, password)
            if result:
                st.session_state.auth = result
                st.rerun()
            st.error("Invalid username or password")
        if not os.environ.get("ADMIN_PASSWORD"):
            st.info("No ADMIN_PASSWORD secret is set, so the first admin password was generated and written to the "
                    "app log (Manage app, then Logs). Set ADMIN_PASSWORD in the app secrets to choose your own.",
                    icon=":material/info:")


@st.dialog("Change password")
def change_password_dialog(username: str, token: str) -> None:
    with st.form("change-password"):
        current = st.text_input("Current password", type="password")
        new = st.text_input("New password", type="password", help=f"At least {MIN_PASSWORD} characters")
        confirm = st.text_input("Confirm new password", type="password")
        submitted = st.form_submit_button("Change password", type="primary")
    if submitted:
        if new != confirm:
            st.error("The passwords do not match.")
            return
        try:
            store.change_password(username, current, new, keep_token=token)
        except ValueError as e:
            st.error(str(e))
            return
        st.success("Password changed. Your other sessions have been signed out.")


user = signed_in_user()
if not user:
    login_view()
    st.stop()

load_rag()
is_admin = user["role"] == "admin"
st.session_state.current_user = user
token = st.session_state.auth["token"]

with st.sidebar:
    st.subheader(user["username"] + (" (admin)" if is_admin else ""))
    st.metric("Tokens used", f"{store.user_usage(user['username'])['total_tokens']:,}")

    options = services.llm_options()
    if options:
        labels = {o["id"]: f"{o['name']} ({o['model']})" for o in options}
        st.selectbox("Model", list(labels), format_func=labels.get, key="llm_id")
    else:
        st.session_state.llm_id = None
        st.warning("No AI model is configured. Answers show document excerpts only." +
                   (" Add one on the Status page." if is_admin else " Ask an admin to add one."), icon=":material/warning:")

    with st.expander("Investor profile", expanded=True):
        st.number_input("Budget (USD)", min_value=0, value=0, step=50_000, key="budget",
                        help="Leave at 0 if you don't want to state a budget.")
        st.selectbox("Investor type", list(services.INVESTOR_TYPES), format_func=services.INVESTOR_TYPES.get, key="investor_type")
        st.selectbox("Risk profile", list(services.RISK_PROFILES), index=1, format_func=services.RISK_PROFILES.get, key="risk_profile")

    with st.container(horizontal=True):
        if st.button("Password", icon=":material/key:"):
            change_password_dialog(user["username"], token)
        if st.button("Sign out", icon=":material/logout:"):
            store.logout(token)
            st.session_state.clear()
            st.rerun()

pages = [
    st.Page("app_pages/chat.py", title="Chat", icon=":material/chat:", default=True),
    st.Page("app_pages/compare.py", title="Compare", icon=":material/bar_chart:"),
    st.Page("app_pages/yield_calculator.py", title="Yield calculator", icon=":material/calculate:"),
]
if is_admin:
    pages.append(st.Page("app_pages/status.py", title="Status", icon=":material/settings:"))
st.navigation(pages).run()

st.divider()
st.caption(DISCLAIMER)
