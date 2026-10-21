import streamlit as st

import advisor

persona = st.session_state.persona
country = st.session_state.country
cfg = st.session_state.model_cfg

st.header("Ask about tax, rules, yields and prices")


def render_sources(sources, live):
    with st.expander(f"Sources ({len(sources)})" if sources else "Sources"):
        for s in sources:
            updated = f" · file updated {s['file_date']}" if s["file_date"] else ""
            st.caption(f"**{s['label']}** ({s['country']}{updated})")
            st.text(s["snippet"] + "...")
        if live:
            st.caption("**Live open data** (World Bank, BIS, currency-api; country-level)")
            st.text(live)


for message in st.session_state.chat:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if message["role"] == "assistant":
            render_sources(message.get("sources", []), message.get("live", ""))
            if message.get("caption"):
                st.caption(message["caption"])

if not st.session_state.chat:
    st.info('Try "What are the buying costs for a foreign investor?" or "How do rents compare with last year?". '
            "For yield and mortgage maths, use the Yield calculator page.", icon=":material/lightbulb:")

if prompt := st.chat_input("Ask about tax, rules, yields...", disabled=cfg is None, submit_mode="disable"):
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        try:
            with st.spinner("Searching the documents..."):
                history = advisor.history_for(st.session_state.chat, persona, country)
                result = advisor.answer_question(prompt, history, persona, country, cfg)
        except Exception as e:
            st.error(f"Could not get an answer: {e}")
            st.stop()

        st.write(result["answer"])
        render_sources(result["sources"], result["live"])
        caption = f"{persona} · {country} · "
        if result["cached"]:
            caption += "saved answer, no tokens used"
        elif result["usage"]:
            usage = result["usage"]
            st.session_state.tokens += usage["total_tokens"]
            caption += f"{cfg['name']} {cfg['model']} · {usage['prompt_tokens']:,} in / {usage['completion_tokens']:,} out"
        else:
            caption += "no model call"
        st.caption(caption)

    ctx = (persona, country)
    st.session_state.chat += [
        {"role": "user", "content": prompt, "ctx": ctx},
        {"role": "assistant", "content": result["answer"], "sources": result["sources"],
         "live": result["live"], "caption": caption, "ctx": ctx},
    ]
