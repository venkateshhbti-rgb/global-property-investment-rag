import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import services  # noqa: E402
from store import Store  # noqa: E402


class FakeRag:
    data_version = "dv1"
    retrieval_tag = "hybrid+rerank"

    def __init__(self):
        self.chat_calls = 0
        self.compare_calls = 0

    def chat(self, messages, profile, llm_cfg):
        self.chat_calls += 1
        self.last_chat = (messages, profile, llm_cfg)
        return {"answer": "Dubai yields look strongest.", "sources": [{"file": "a.pdf", "region": "Dubai", "type": "PDF", "preview": "x"}],
                "success": True, "llm": llm_cfg["name"] if llm_cfg else None,
                "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120} if llm_cfg else None,
                "clarifying_questions": None}

    def compare_regions(self, metric, regions, profile, llm_cfg):
        self.compare_calls += 1
        return {"answer": f"{metric}: compared {regions}", "sources": [], "success": True, "llm": llm_cfg["name"],
                "usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60}}


@pytest.fixture
def env(monkeypatch):
    import store as store_module
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # The settings object is read once at import, so override it directly: a real .env key must never leak into tests.
    monkeypatch.setattr(store_module.settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(store_module.settings, "ADMIN_PASSWORD", "Admin-Pass-1")
    store = Store(os.path.join(tempfile.mkdtemp(), "s.json"))
    assert store.list_llms() == [], "test store must start without any model"
    store.add_user("bob", "bobpass-1", "user")
    llm = store.add_llm("Test model", "openai", "gpt-4o-mini", "fake-key")
    return store, FakeRag(), {"username": "bob"}, llm["id"]


PROFILE = {"budget": 500000, "type": "individual", "risk_profile": "moderate"}
MSGS = [{"role": "user", "content": "Where should I invest in Dubai?"}]


def test_build_profile_treats_zero_budget_as_unset():
    assert services.build_profile(0, "individual", "moderate")["budget"] is None
    assert services.build_profile(250000, "relocation", "aggressive") == {"budget": 250000, "type": "relocation", "risk_profile": "aggressive"}


def test_answers_text_matches_the_react_form_format():
    qs = [{"question": "Which city?", "options": []}, {"question": "Holding period?", "options": []}]
    text = services.answers_text(qs, ["Dubai", "  "])
    assert text == "My answers:\n- Which city? Dubai\n- Holding period? No preference\nPlease give me the full analysis."


def test_chat_turn_records_tokens_for_the_user_and_the_model(env):
    store, rag, user, llm_id = env
    r = services.chat_turn(rag, user, MSGS, PROFILE, llm_id, store_=store)
    assert r["cached"] is False and r["usage"]["total_tokens"] == 120
    assert store.user_usage("bob")["total_tokens"] == 120
    assert store.list_llms()[0]["usage"]["total_tokens"] == 120


def test_repeated_chat_is_served_from_saved_answers_without_tokens(env):
    store, rag, user, llm_id = env
    services.chat_turn(rag, user, MSGS, PROFILE, llm_id, store_=store)
    again = services.chat_turn(rag, user, MSGS, PROFILE, llm_id, store_=store)
    assert again["cached"] is True and again["usage"] is None
    assert rag.chat_calls == 1
    assert store.user_usage("bob")["total_tokens"] == 120


def test_a_different_profile_is_not_served_from_saved_answers(env):
    store, rag, user, llm_id = env
    services.chat_turn(rag, user, MSGS, PROFILE, llm_id, store_=store)
    services.chat_turn(rag, user, MSGS, {**PROFILE, "risk_profile": "aggressive"}, llm_id, store_=store)
    assert rag.chat_calls == 2


def test_no_model_means_no_tokens_and_no_saved_answer(env):
    store, rag, user, llm_id = env
    store.delete_llm(llm_id)
    r = services.chat_turn(rag, user, MSGS, PROFILE, None, store_=store)
    assert r["usage"] is None and store.cache_size() == 0


def test_compare_turn_records_tokens_and_caches(env):
    store, rag, user, llm_id = env
    first = services.compare_turn(rag, user, "rental yields", ["Dubai", "Mumbai"], PROFILE, llm_id, store_=store)
    second = services.compare_turn(rag, user, "rental yields", ["Mumbai", "Dubai"], PROFILE, llm_id, store_=store)
    assert first["cached"] is False and second["cached"] is True
    assert rag.compare_calls == 1 and store.user_usage("bob")["total_tokens"] == 60


def test_retired_openai_models_are_upgraded(env):
    store, rag, user, llm_id = env
    store.set_llm_model(llm_id, "gpt-3.5-turbo")
    services.prepare_providers(store)
    assert store.list_llms()[0]["model"] == "gpt-4o-mini"


def test_claude_provider_is_added_from_the_environment_once(env, monkeypatch):
    store, *_ = env
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key-1")
    services.prepare_providers(store)
    services.prepare_providers(store)
    claude = [l for l in store.list_llms() if l["provider"] == "anthropic"]
    assert len(claude) == 1 and claude[0]["name"] == services.CLAUDE_PROVIDER_NAME
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key-2")
    services.prepare_providers(store)
    assert store.get_llm_config(claude[0]["id"])["api_key"] == "claude-key-2"


def test_llm_options_lists_only_enabled_models(env):
    store, rag, user, llm_id = env
    assert [o["id"] for o in services.llm_options(store)] == [llm_id]
    store.set_llm_enabled(llm_id, False)
    assert services.llm_options(store) == []
