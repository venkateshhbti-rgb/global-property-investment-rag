import streamlit as st

import query
from llm_client import call_llm
from market_data import market_data
from store import MIN_PASSWORD, store

user = st.session_state.current_user
if user["role"] != "admin":
    st.error("This page is for admins only.", icon=":material/lock:")
    st.stop()

rag = query.get_rag()
st.header("System status")
st.caption("Documents, search quality, live data, AI models and users.")

PROVIDERS = {"openai": "OpenAI or compatible", "anthropic": "Anthropic (Claude)", "gemini": "Google Gemini"}
DEFAULT_MODELS = {"openai": "gpt-4o-mini", "anthropic": "claude-sonnet-5-5", "gemini": "gemini-2.0-flash"}


def pct(ind, key):
    return f"{ind[key]['value']:.1f}% ({ind[key]['year']})" if key in ind else "-"


# ---------- Documents ----------
with st.container(border=True):
    st.subheader("Documents")
    stats = rag.get_system_stats()
    with st.container(horizontal=True):
        st.metric("Passages", f"{stats['total_documents']:,}", border=True)
        st.metric("Markets", len(stats["by_region"]), border=True)
        st.metric("Data size", f"{stats['total_characters'] / 1_048_576:.1f} MB", border=True)
        st.metric("Saved answers", store.cache_size(), border=True)
    if stats["by_region"]:
        st.dataframe([{"Market": r, "Passages": n} for r, n in stats["by_region"].items()], hide_index=True)
    with st.container(horizontal=True):
        if st.button("Reload documents", icon=":material/refresh:"):
            with st.spinner("Reloading documents..."):
                rag.reload_documents()
                cleared = store.cache_clear()
            st.toast(f"Documents reloaded. Cleared {cleared} saved answers.")
            st.rerun()
        if st.button("Clear saved answers", icon=":material/cleaning_services:", disabled=store.cache_size() == 0):
            st.toast(f"Cleared {store.cache_clear()} saved answers")
            st.rerun()

# ---------- Retrieval ----------
with st.container(border=True):
    st.subheader("Retrieval quality")
    r = rag.retrieval_status()
    labels = {
        "hybrid+rerank": "Hybrid (keyword + semantic) with reranker",
        "hybrid": "Hybrid (keyword + semantic)",
        "keyword+rerank": "Keyword search with reranker (semantic index still building)",
        "keyword": "Keyword search only",
    }
    st.write(f"**Mode:** {labels.get(r['mode'], r['mode'])}")
    st.write(f"**Embeddings:** {r.get('provider') or 'not configured'} · **Reranker:** {r.get('reranker', '-')}")
    total = max(r.get("total", 0), 1)
    st.progress(min(1.0, r.get("embedded", 0) / total), text=f"{r.get('embedded', 0):,} of {r.get('total', 0):,} passages indexed")
    if r.get("error"):
        st.error(r["error"])
    if r.get("query_error"):
        st.error(f"{r['query_error']}. Check the API key under AI models.")
    st.button("Refresh status", icon=":material/refresh:", key="refresh-retrieval")

# ---------- Live data ----------
with st.container(border=True):
    st.subheader("Live market data")
    st.caption("Country-level figures from the World Bank, the BIS house-price index and currency-api, refreshed daily. "
               "If a market matches the wrong country, add it to data/_market_overrides.json, for example {\"Dubai\": \"AE\"}.")
    rows = []
    for m in market_data.snapshot(rag.regions):
        ind, hp, fx = m.get("indicators", {}), m.get("house_prices"), m.get("fx")
        rows.append({
            "Market": m["region"],
            "Matched to": f"{m.get('country', '-')} / {m.get('currency') or '-'}",
            "Inflation": pct(ind, "inflation"),
            "GDP growth": pct(ind, "gdp_growth"),
            "Lending rate": pct(ind, "lending_rate"),
            "House prices y/y": f"{hp['yoy']:.1f}% ({hp['period']})" if hp else "n/a",
            "FX per USD (12m)": (f"{fx['rate']:.2f}" + (f" ({fx['change_12m_pct']:+}%)" if fx.get("change_12m_pct") is not None else "")) if fx else "-",
        })
    if rows:
        st.dataframe(rows, hide_index=True)
    else:
        st.caption("No data yet. Press the button below, it takes about 30 seconds.")
    if st.button("Refresh live data", icon=":material/cloud_sync:"):
        with st.spinner("Refreshing from the World Bank, BIS and currency-api..."):
            market_data.refresh(rag.regions, force=True)
        st.rerun()

# ---------- AI models ----------
with st.container(border=True):
    st.subheader("AI models")
    st.caption("Users pick from the enabled models in the sidebar. API keys are stored on the server and never shown again.")
    providers = store.list_llms()
    if not providers:
        st.info("No models yet. Add one below, until then the app only shows document excerpts.")
    for p in providers:
        with st.container(border=True):
            head = st.columns([3, 2, 2, 1])
            head[0].markdown(f"**{p['name']}**  \n{p['provider']} / {p['model']}")
            head[1].caption(f"Key {p['api_key_masked']}")
            head[2].caption(f"{p['usage']['total_tokens']:,} tokens · {p['usage']['requests']} requests")
            head[3].markdown(":green[Enabled]" if p["enabled"] else ":gray[Disabled]")
            with st.container(horizontal=True):
                if st.button("Test", key=f"test-{p['id']}", icon=":material/bolt:", disabled=not p["enabled"]):
                    try:
                        _, usage = call_llm(store.get_llm_config(p["id"]), "Reply with the single word: ok",
                                            [{"role": "user", "content": "ping"}], max_tokens=16)
                        st.success(f"Connected ({usage['total_tokens']} tokens used)")
                    except Exception as e:
                        st.error(str(e))
                if st.button("Disable" if p["enabled"] else "Enable", key=f"toggle-{p['id']}", icon=":material/power_settings_new:"):
                    store.set_llm_enabled(p["id"], not p["enabled"])
                    st.rerun()
                if st.button("Delete", key=f"delete-{p['id']}", icon=":material/delete:"):
                    store.delete_llm(p["id"])
                    st.rerun()
            with st.expander("Change model or API key"):
                with st.form(f"edit-{p['id']}"):
                    model = st.text_input("Model", value=p["model"])
                    new_key = st.text_input("New API key (leave empty to keep the current one)", type="password")
                    if st.form_submit_button("Save and test"):
                        try:
                            store.set_llm_model(p["id"], model)
                            if new_key.strip():
                                store.set_llm_key(p["id"], new_key)
                            _, usage = call_llm(store.get_llm_config(p["id"]), "Reply with the single word: ok",
                                                [{"role": "user", "content": "ping"}], max_tokens=16)
                            st.success("Saved. The connection works.")
                        except Exception as e:
                            st.error(f"Saved, but the test failed: {e}")

    with st.expander("Add a model", expanded=not providers):
        with st.form("add-llm", clear_on_submit=True):
            name = st.text_input("Display name", placeholder="GPT-4o mini")
            provider = st.selectbox("Provider", list(PROVIDERS), format_func=PROVIDERS.get)
            model = st.text_input("Model", value="", placeholder="for example " + DEFAULT_MODELS[provider])
            api_key = st.text_input("API key", type="password")
            base_url = st.text_input("Base URL (optional, for OpenAI-compatible servers)")
            if st.form_submit_button("Add model", icon=":material/add:"):
                try:
                    store.add_llm(name, provider, model or DEFAULT_MODELS[provider], api_key, base_url)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

# ---------- Users ----------
with st.container(border=True):
    st.subheader("Users")
    st.caption(f"Passwords need at least {MIN_PASSWORD} characters.")
    users = store.list_users()
    st.dataframe([{"Username": u["username"], "Role": u["role"], "Tokens used": u["usage"]["total_tokens"],
                   "Requests": u["usage"]["requests"]} for u in users], hide_index=True)

    with st.expander("Add a user"):
        with st.form("add-user", clear_on_submit=True):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            role = st.selectbox("Role", ["user", "admin"])
            if st.form_submit_button("Add user", icon=":material/person_add:"):
                try:
                    store.add_user(username, password, role)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    with st.expander("Reset a password or delete a user"):
        target = st.selectbox("User", [u["username"] for u in users], key="target-user")
        with st.form("reset-password", clear_on_submit=True):
            new_password = st.text_input(f"New password for {target}", type="password")
            if st.form_submit_button("Reset password", icon=":material/key:"):
                try:
                    store.reset_password(target, new_password)
                    st.success(f"Password reset for {target}. They are signed out everywhere.")
                except ValueError as e:
                    st.error(str(e))
        confirm = st.checkbox(f"I want to delete {target}", key="confirm-delete")
        if st.button("Delete user", icon=":material/delete:", disabled=not confirm or target == user["username"]):
            try:
                store.delete_user(target)
                st.rerun()
            except ValueError as e:
                st.error(str(e))
        if target == user["username"]:
            st.caption("You can't delete your own account.")
