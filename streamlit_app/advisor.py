"""The question -> answer workflow. No Streamlit imports, so it can be unit-tested."""
from typing import Any, Dict, List, Tuple

import cache
import llm
import query
from prompts import PERSONAS, PROMPT_VERSION

MAX_ANSWER_TOKENS = 700
Hits = List[Tuple[str, Dict[str, Any]]]


def format_hits(hits: Hits) -> str:
    """Passages as the LLM sees them, each labelled so it can cite [file pN]."""
    blocks = []
    for text, meta in hits:
        page = f" p{meta['page']}" if meta["page"] else ""
        blocks.append(f"[{meta['source_file']}{page}]\n{text[:700]}")
    return "\n\n".join(blocks)


def source_records(hits: Hits) -> List[Dict[str, Any]]:
    return [{
        "label": meta["source_file"] + (f" p{meta['page']}" if meta["page"] else ""),
        "country": meta["country"],
        "file_date": meta["file_date"],
        "snippet": " ".join(text.split())[:240],
    } for text, meta in hits]


def history_for(chat: List[Dict[str, Any]], persona: str, country: str) -> List[Dict[str, str]]:
    """Earlier turns written under the same persona and country. Turns from another persona would otherwise act as
    format examples and the new persona's structure would be ignored."""
    return [{"role": m["role"], "content": m["content"]} for m in chat if m.get("ctx") == (persona, country)]


def answer_question(question: str, history: List[Dict[str, str]], persona: str, country: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Filter by country, retrieve, add live data, ask the model. Repeated questions come from the SQLite cache."""
    recent_questions = ([m["content"] for m in history if m["role"] == "user"] + [question])[-3:]

    key = cache.make_key(PROMPT_VERSION, persona, country, f"{cfg['provider']}:{cfg['model']}",
                         query.cache_fingerprint(), questions=recent_questions)
    # An identical question asked on its own earlier (no history) is reused even when the chat has grown since.
    standalone_key = cache.make_key(PROMPT_VERSION, persona, country, f"{cfg['provider']}:{cfg['model']}",
                                    query.cache_fingerprint(), questions=[question])
    saved = cache.get(key) or cache.get(standalone_key)
    if saved:
        return {**saved, "cached": True}

    hits = query.search(" ".join(recent_questions), country, k=5)
    if not hits:
        where = "the loaded documents" if country == query.ALL_MARKETS else f"the {country} documents"
        return {"answer": f"I don't have anything on that in {where}. Try another country or add the relevant document.",
                "sources": [], "live": "", "usage": None, "cached": False}

    live = query.live_context(country, hits)
    system = PERSONAS[persona] + f"\n\nSelected country: {country}. Countries loaded: {', '.join(query.countries())}."
    user_message = (f"CONTEXT:\n{format_hits(hits)}\n\n"
                    f"LIVE MARKET DATA:\n{live or 'not available right now'}\n\n"
                    f"Question: {question}")
    messages = [{"role": m["role"], "content": m["content"]} for m in history[-6:]]
    text, usage = llm.complete(cfg, system, messages + [{"role": "user", "content": user_message}], MAX_ANSWER_TOKENS)

    result = {"answer": text, "sources": source_records(hits), "live": live, "usage": usage}
    cache.put(key, result)
    return {**result, "cached": False}
