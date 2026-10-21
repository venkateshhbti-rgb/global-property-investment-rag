import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import advisor  # noqa: E402
import cache  # noqa: E402

CFG = {"provider": "openai", "model": "test-model", "api_key": "x", "name": "Test"}
HIT = ("Residential lease values grew 8% year on year.",
       {"source_file": "report.pdf", "page": 12, "country": "Abu Dhabi", "doc_type": "PDF", "file_date": "2026-01-01"})


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(cache, "DB_PATH", tmp_path / "answers.sqlite")
    monkeypatch.setattr(advisor.query, "cache_fingerprint", lambda: "fp1")
    monkeypatch.setattr(advisor.query, "live_context", lambda country, hits: "Abu Dhabi | Inflation: 1.3% (World Bank, 2025)")
    monkeypatch.setattr(advisor.query, "countries", lambda: ["Abu Dhabi", "Dubai"])
    calls = {"llm": 0, "search": []}

    def fake_search(q, country, k=5):
        calls["search"].append((q, country))
        return [HIT]

    def fake_complete(cfg, system, messages, max_tokens):
        calls["llm"] += 1
        calls["system"], calls["messages"] = system, messages
        return "Rents rose 8% [report.pdf p12].", {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}

    monkeypatch.setattr(advisor.query, "search", fake_search)
    monkeypatch.setattr(advisor.llm, "complete", fake_complete)
    return calls


def test_format_hits_labels_each_passage_for_citation():
    text = advisor.format_hits([HIT])
    assert text.startswith("[report.pdf p12]")
    assert "Residential lease values" in text


def test_page_label_is_omitted_when_missing():
    meta = {**HIT[1], "page": None}
    assert advisor.format_hits([(HIT[0], meta)]).startswith("[report.pdf]\n")
    assert advisor.source_records([(HIT[0], meta)])[0]["label"] == "report.pdf"


def test_answer_uses_persona_country_live_data_and_returns_sources(isolated):
    r = advisor.answer_question("How are rents moving?", [], "Advisor", "Abu Dhabi", CFG)
    assert r["answer"].startswith("Rents rose")
    assert r["cached"] is False and r["usage"]["total_tokens"] == 120
    assert r["sources"][0]["label"] == "report.pdf p12"
    assert isolated["search"][0][1] == "Abu Dhabi"
    assert "wealth advisor" in isolated["system"]
    assert "Selected country: Abu Dhabi" in isolated["system"]
    last = isolated["messages"][-1]["content"]
    assert "CONTEXT:" in last and "LIVE MARKET DATA:" in last and "Inflation: 1.3%" in last


def test_repeated_question_is_served_from_cache_without_calling_the_model(isolated):
    advisor.answer_question("How are rents moving?", [], "Investor", "Dubai", CFG)
    again = advisor.answer_question("  how are RENTS moving??  ", [], "Investor", "Dubai", CFG)
    assert again["cached"] is True
    assert isolated["llm"] == 1


@pytest.mark.parametrize("change", [
    {"persona": "Advisor"}, {"country": "Abu Dhabi"}, {"cfg": {**CFG, "model": "other"}},
])
def test_changing_persona_country_or_model_is_a_cache_miss(isolated, change):
    base = {"persona": "Investor", "country": "Dubai", "cfg": CFG}
    advisor.answer_question("How are rents moving?", [], **base)
    advisor.answer_question("How are rents moving?", [], **{**base, **change})
    assert isolated["llm"] == 2


def test_new_data_fingerprint_invalidates_saved_answers(isolated, monkeypatch):
    advisor.answer_question("How are rents moving?", [], "Investor", "Dubai", CFG)
    monkeypatch.setattr(advisor.query, "cache_fingerprint", lambda: "fp2")
    advisor.answer_question("How are rents moving?", [], "Investor", "Dubai", CFG)
    assert isolated["llm"] == 2


def test_no_matching_passages_skips_the_model(isolated, monkeypatch):
    monkeypatch.setattr(advisor.query, "search", lambda q, country, k=5: [])
    r = advisor.answer_question("Something unrelated", [], "Investor", "Dubai", CFG)
    assert "don't have anything" in r["answer"]
    assert r["usage"] is None and isolated["llm"] == 0


def test_follow_up_search_uses_recent_user_turns(isolated):
    history = [{"role": "user", "content": "Tell me about Dubai rents"},
               {"role": "assistant", "content": "Rents rose."}]
    advisor.answer_question("and service charges?", history, "Investor", "Dubai", CFG)
    assert "Dubai rents" in isolated["search"][0][0] and "service charges" in isolated["search"][0][0]


def test_same_question_repeated_later_in_the_chat_is_still_saved(isolated):
    advisor.answer_question("How are rents moving?", [], "Investor", "Dubai", CFG)
    history = [{"role": "user", "content": "How are rents moving?"}, {"role": "assistant", "content": "Rents rose."},
               {"role": "user", "content": "And service charges?"}, {"role": "assistant", "content": "They are 12 per sqft."}]
    again = advisor.answer_question("How are rents moving?", history, "Investor", "Dubai", CFG)
    assert again["cached"] is True
    assert isolated["llm"] == 1


def test_history_only_includes_turns_from_the_same_persona_and_country():
    chat = [
        {"role": "user", "content": "q1", "ctx": ("Investor", "Dubai")},
        {"role": "assistant", "content": "a1", "ctx": ("Investor", "Dubai")},
        {"role": "user", "content": "q2", "ctx": ("Advisor", "Dubai")},
        {"role": "assistant", "content": "a2", "ctx": ("Advisor", "Dubai")},
        {"role": "user", "content": "q3", "ctx": ("Advisor", "Mumbai")},
    ]
    assert [m["content"] for m in advisor.history_for(chat, "Advisor", "Dubai")] == ["q2", "a2"]
    assert advisor.history_for(chat, "Relocation consultant", "Dubai") == []


def test_prompts_tell_the_model_to_copy_real_file_labels():
    from prompts import PERSONAS
    for prompt in PERSONAS.values():
        assert "copying the label" in prompt and "[file pN]" not in prompt
