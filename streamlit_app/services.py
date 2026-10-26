"""What the pages need, mirroring the FastAPI endpoints. No Streamlit imports, so it is unit-tested."""
import os
from typing import Any, Dict, List, Optional

import query  # noqa: F401  (configures paths and puts the backend on sys.path; must come first)
from store import make_cache_key, store as default_store

INVESTOR_TYPES = {
    "individual": "Individual investor",
    "wealth_advisor": "Wealth advisor",
    "relocation": "Relocation consultant",
}
RISK_PROFILES = {"conservative": "Conservative", "moderate": "Moderate", "aggressive": "Aggressive"}
COMPARE_METRICS = [
    "rental yields", "property prices", "market growth", "affordability",
    "investment returns", "transaction volume", "regulatory environment", "ROI potential",
]
STARTER_QUESTIONS = [
    "Compare rental yields across available markets",
    "What costs should I consider when buying a property?",
]
RETIRED_MODELS = {"gpt-3.5-turbo": "gpt-4o-mini"}
CLAUDE_PROVIDER_NAME = "Claude (from secrets)"


def _self_contained(rag, question: str) -> bool:
    """A question that names a market and is not a short follow-up means the same thing in any conversation."""
    return len(question.split()) >= 5 and any(r.lower() in question.lower() for r in rag.regions)


def build_profile(budget: Optional[float], investor_type: str, risk_profile: str) -> Dict[str, Any]:
    return {"budget": int(budget) if budget else None, "type": investor_type, "risk_profile": risk_profile}


def prepare_providers(store_=None) -> None:
    """Run once per start: add Claude from secrets, and move providers off models OpenAI has retired."""
    store_ = store_ or default_store
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        existing = next((l for l in store_.data["llms"] if l["name"] == CLAUDE_PROVIDER_NAME), None)
        if existing is None:
            store_.add_llm(CLAUDE_PROVIDER_NAME, "anthropic", os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5"), key)
        elif existing["api_key"] != key:
            store_.set_llm_key(existing["id"], key)
    for llm in list(store_.data["llms"]):
        if llm["provider"] == "openai" and llm["model"] in RETIRED_MODELS:
            store_.set_llm_model(llm["id"], RETIRED_MODELS[llm["model"]])


def llm_options(store_=None) -> List[Dict[str, str]]:
    store_ = store_ or default_store
    return [{"id": l["id"], "name": l["name"], "model": l["model"]} for l in store_.list_llms(include_disabled=False)]


def answers_text(questions: List[Dict[str, Any]], answers: List[str]) -> str:
    """The message sent when the user fills in the clarifying-question form."""
    lines = [f"- {q['question']} {a.strip() or 'No preference'}" for q, a in zip(questions, answers)]
    return "My answers:\n" + "\n".join(lines) + "\nPlease give me the full analysis."


def chat_turn(rag, user: Dict[str, Any], messages: List[Dict[str, str]], profile: Dict[str, Any],
              llm_id: Optional[str], store_=None) -> Dict[str, Any]:
    store_ = store_ or default_store
    llm_cfg = store_.get_llm_config(llm_id)

    key = standalone_key = None
    if llm_cfg:
        fingerprint = query.fingerprint(rag)
        user_turns = [m["content"] for m in messages[-8:] if m["role"] == "user"]
        key = make_cache_key("chat", user_turns, profile, llm_cfg, fingerprint)
        last_question = user_turns[-1] if user_turns else ""
        # A self-contained question is also saved on its own, so asking it again later in a longer chat is still free.
        if _self_contained(rag, last_question):
            standalone_key = make_cache_key("chat-single", [last_question], profile, llm_cfg, fingerprint)
        saved = store_.cache_get(key) or (store_.cache_get(standalone_key) if standalone_key else None)
        if saved:
            return {"answer": saved["answer"], "sources": saved["sources"], "usage": None, "llm": saved["llm"],
                    "questions": saved.get("clarifying_questions"), "cached": True, "success": True}

    result = rag.chat(messages, profile, llm_cfg)
    if result.get("usage") and llm_cfg:
        store_.record_usage(user["username"], llm_cfg["id"], result["usage"])
    if key and result["success"] and result["usage"]:
        payload = {"answer": result["answer"], "sources": result["sources"], "llm": result["llm"],
                   "clarifying_questions": result.get("clarifying_questions")}
        store_.cache_put(key, payload)
        if standalone_key and not payload["clarifying_questions"]:
            store_.cache_put(standalone_key, payload)
    return {"answer": result["answer"], "sources": result["sources"], "usage": result["usage"], "llm": result["llm"],
            "questions": result.get("clarifying_questions"), "cached": False, "success": result["success"]}


def compare_turn(rag, user: Dict[str, Any], metric: str, regions: List[str], profile: Dict[str, Any],
                 llm_id: Optional[str], store_=None) -> Dict[str, Any]:
    store_ = store_ or default_store
    llm_cfg = store_.get_llm_config(llm_id)

    key = None
    if llm_cfg:
        key = make_cache_key("compare", [metric] + sorted(regions), profile, llm_cfg, query.fingerprint(rag))
        saved = store_.cache_get(key)
        if saved:
            return {"answer": saved["answer"], "sources": saved["sources"], "usage": None, "llm": saved["llm"],
                    "cached": True, "success": True}

    result = rag.compare_regions(metric, regions, profile, llm_cfg)
    if result.get("usage") and llm_cfg:
        store_.record_usage(user["username"], llm_cfg["id"], result["usage"])
    if key and result["success"] and result["usage"]:
        store_.cache_put(key, {"answer": result["answer"], "sources": result["sources"], "llm": result["llm"]})
    return {"answer": result["answer"], "sources": result["sources"], "usage": result["usage"], "llm": result["llm"],
            "cached": False, "success": result["success"]}
