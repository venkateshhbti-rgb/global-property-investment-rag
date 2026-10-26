import streamlit as st

import query
import services
from ui import render_sources, safe, usage_caption

user = st.session_state.current_user
rag = query.get_rag()
llm_id = st.session_state.get("llm_id")
profile = services.build_profile(st.session_state.budget, st.session_state.investor_type, st.session_state.risk_profile)

st.header("Regional comparison")
st.caption("Compare property investment metrics across your markets.")

if len(rag.regions) < 1:
    st.warning("No documents are loaded, so there is nothing to compare.", icon=":material/folder_off:")
    st.stop()

st.session_state.setdefault("metric", "rental yields")


def pick_metric():
    if st.session_state.metric_pill:
        st.session_state.metric = st.session_state.metric_pill


st.text_input("Metric to compare", key="metric", placeholder="Enter a metric or pick a suggestion")
st.pills("Suggestions", services.COMPARE_METRICS, key="metric_pill", on_change=pick_metric)
regions = st.multiselect("Markets", rag.regions, default=rag.regions[:2], key="compare_regions")

if st.button("Compare", type="primary", icon=":material/search:", disabled=not st.session_state.metric.strip() or not regions):
    with st.spinner("Comparing..."):
        st.session_state.compare_result = {
            "metric": st.session_state.metric.strip(), "regions": regions,
            **services.compare_turn(rag, user, st.session_state.metric.strip(), regions, profile, llm_id),
        }

result = st.session_state.compare_result
if result:
    with st.container(border=True):
        st.subheader("Comparison results")
        st.caption(f"{result['metric']} · {', '.join(result['regions'])}")
        st.markdown(safe(result["answer"]))
        render_sources(result["sources"])
        if usage_caption(result):
            st.caption(usage_caption(result))
else:
    st.info("Select a metric and markets, then press Compare.", icon=":material/bar_chart:")
