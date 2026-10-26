import streamlit as st

import query
import services
from ui import render_sources, safe, usage_caption

user = st.session_state.current_user
rag = query.get_rag()
llm_id = st.session_state.get("llm_id")
profile = services.build_profile(st.session_state.budget, st.session_state.investor_type, st.session_state.risk_profile)
messages = st.session_state.chat

st.header("Investment workspace")
st.caption("Explore markets. Compare opportunities. Follow the evidence.")

if not rag.regions:
    st.warning("No documents are loaded, so the consultant has nothing to search. Add folders of documents under "
               "`data/` (one folder per city or country) and reload them on the Status page.", icon=":material/folder_off:")


def question_form(questions, index):
    with st.form(f"clarify-{index}"):
        answers = []
        for j, q in enumerate(questions):
            st.markdown(f"**{j + 1}. {safe(q['question'])}**")
            choice = st.pills("Options", q["options"], key=f"pill-{index}-{j}", label_visibility="collapsed") if q["options"] else None
            typed = st.text_input("Or type your own answer", key=f"typed-{index}-{j}")
            answers.append(typed.strip() or choice or "")
        if st.form_submit_button("Get my analysis", type="primary"):
            st.session_state.pending = services.answers_text(questions, answers)
            st.rerun()


if not messages:
    with st.chat_message("assistant"):
        st.markdown(
            "Welcome to Property Investment Consultant! I can help you with:\n\n"
            "- Property market analysis for the cities and countries in your data\n"
            "- Rental yield comparisons\n"
            "- Investment recommendations based on your budget\n"
            "- Market trends and growth potential\n"
            "- Regulatory and tax information\n\n"
            "What would you like to know about real estate investment?"
        )
    with st.container(horizontal=True):
        for starter in services.STARTER_QUESTIONS:
            if st.button(starter, key=f"starter-{starter}"):
                st.session_state.pending = starter
                st.rerun()

for i, message in enumerate(messages):
    with st.chat_message(message["role"]):
        st.markdown(safe(message["content"]))
        if message["role"] == "assistant":
            render_sources(message.get("sources", []))
            if message.get("caption"):
                st.caption(message["caption"])
            if message.get("questions") and i == len(messages) - 1:
                question_form(message["questions"], i)

prompt = st.chat_input("Ask about property markets, or answer the questions above...", submit_mode="disable")
text = st.session_state.pop("pending", None) or prompt
if text:
    messages.append({"role": "user", "content": text})
    with st.chat_message("user"):
        st.markdown(safe(text))
    with st.chat_message("assistant"):
        with st.spinner("Searching the documents..."):
            history = [{"role": m["role"], "content": m["content"]} for m in messages]
            result = services.chat_turn(rag, user, history, profile, llm_id)
    messages.append({
        "role": "assistant", "content": result["answer"], "sources": result["sources"],
        "caption": usage_caption(result), "questions": result["questions"],
    })
    st.rerun()
