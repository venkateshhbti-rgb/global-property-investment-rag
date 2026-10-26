"""Small Streamlit helpers shared by the pages."""
from typing import Any, Dict, List

import streamlit as st


def safe(text: str) -> str:
    """Streamlit treats $...$ as maths, which garbles dollar amounts. Escape the dollar signs."""
    return text.replace("$", "\\$")


def render_sources(sources: List[Dict[str, Any]]) -> None:
    if not sources:
        return
    with st.expander(f"Sources ({len(sources)})"):
        for s in sources:
            st.caption(f"**{s['file']}** · {s['region']} · {s['type']}")
            if s.get("preview"):
                st.text(s["preview"])


def usage_caption(result: Dict[str, Any]) -> str:
    if result.get("cached"):
        return "Saved answer, no tokens used"
    usage = result.get("usage")
    if not usage:
        return ""
    return f"{result['llm']} · {usage['prompt_tokens']:,} in / {usage['completion_tokens']:,} out · {usage['total_tokens']:,} tokens"
