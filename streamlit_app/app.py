import os

import streamlit as st

st.set_page_config(page_title="Property investment advisor", page_icon=":material/home_work:", layout="wide")

DISCLAIMER = ("Informational only, not financial, tax or legal advice. "
              "Figures come from the loaded documents and open data and may be out of date.")


def _load_secrets() -> None:
    """Copy keys from .streamlit/secrets.toml (or Streamlit Cloud secrets) into the environment."""
    try:
        for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "CLAUDE_MODEL", "OPENAI_CHAT_MODEL"):
            if key in st.secrets:
                os.environ.setdefault(key, str(st.secrets[key]))
    except Exception:
        pass  # no secrets file: fall back to environment variables and backend/.env


_load_secrets()

import cache  # noqa: E402
import llm  # noqa: E402
import query  # noqa: E402
from prompts import PERSONAS  # noqa: E402

st.session_state.setdefault("chat", [])
st.session_state.setdefault("tokens", 0)


@st.cache_resource(show_spinner="Loading documents and the search index (about a minute the first time)...")
def load_rag():
    return query.get_rag()


models = llm.available_models()
persona = st.sidebar.selectbox("I am a...", list(PERSONAS), key="persona")
load_rag()
country = st.sidebar.selectbox("Country", [query.ALL_MARKETS] + query.countries(), key="country")
if models:
    model_label = st.sidebar.selectbox("Model", list(models), key="model_label")
    st.session_state.model_cfg = models[model_label]
else:
    st.session_state.model_cfg = None
    st.sidebar.error("No API key found. Add ANTHROPIC_API_KEY or OPENAI_API_KEY to .streamlit/secrets.toml.")

status = query.status()
st.sidebar.divider()
st.sidebar.caption(f"Search: {status['mode']} ({status.get('embedded', 0):,}/{status.get('total', 0):,} indexed)")
st.sidebar.caption(f"Tokens this session: {st.session_state.tokens:,}")
if st.sidebar.button("Clear chat", icon=":material/delete:"):
    st.session_state.chat = []
    st.rerun()
if st.sidebar.button(f"Clear saved answers ({cache.size()})", icon=":material/cleaning_services:"):
    cache.clear()
    st.rerun()

page = st.navigation([
    st.Page("app_pages/chat.py", title="Chat", icon=":material/chat:", default=True),
    st.Page("app_pages/yield_calculator.py", title="Yield calculator", icon=":material/calculate:"),
])
page.run()

st.divider()
st.caption(DISCLAIMER)
