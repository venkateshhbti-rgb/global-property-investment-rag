from typing import Any, Dict, List, Tuple

import requests

TIMEOUT = 60


class LLMError(Exception):
    pass


def _error_message(resp: requests.Response) -> str:
    try:
        body = resp.json()
        err = body.get("error", body)
        if isinstance(err, dict):
            return err.get("message") or str(err)
        return str(err)
    except ValueError:
        return resp.text[:300]


def _normalize(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Drop leading assistant turns and merge consecutive same-role turns."""
    out: List[Dict[str, str]] = []
    for m in messages:
        if m["role"] not in ("user", "assistant") or not m["content"].strip():
            continue
        if not out and m["role"] != "user":
            continue
        if out and out[-1]["role"] == m["role"]:
            out[-1] = {"role": m["role"], "content": out[-1]["content"] + "\n" + m["content"]}
        else:
            out.append({"role": m["role"], "content": m["content"]})
    return out


def _post(url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> requests.Response:
    try:
        return requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise LLMError(f"Could not reach the LLM provider: {e}")


def _openai(cfg, system, messages, max_tokens, temperature):
    base = cfg.get("base_url") or "https://api.openai.com/v1"
    url = f"{base}/chat/completions"
    headers = {"Authorization": f"Bearer {cfg['api_key']}"}
    payload = {
        "model": cfg["model"],
        "messages": [{"role": "system", "content": system}] + messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    resp = _post(url, headers, payload)
    if resp.status_code == 400 and "max_completion_tokens" in resp.text:
        payload.pop("max_tokens")
        payload.pop("temperature", None)
        payload["max_completion_tokens"] = max_tokens * 4  # reasoning models spend tokens thinking
        resp = _post(url, headers, payload)
    if resp.status_code != 200:
        raise LLMError(_error_message(resp))
    body = resp.json()
    usage = body.get("usage", {})
    return body["choices"][0]["message"]["content"] or "", {
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
    }


def _anthropic(cfg, system, messages, max_tokens, temperature):
    headers = {"x-api-key": cfg["api_key"], "anthropic-version": "2023-06-01"}
    payload = {
        "model": cfg["model"], "max_tokens": max_tokens, "temperature": temperature,
        "system": system, "messages": messages,
    }
    resp = _post("https://api.anthropic.com/v1/messages", headers, payload)
    if resp.status_code != 200:
        raise LLMError(_error_message(resp))
    body = resp.json()
    text = "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")
    usage = body.get("usage", {})
    return text, {
        "prompt_tokens": usage.get("input_tokens", 0),
        "completion_tokens": usage.get("output_tokens", 0),
    }


def _gemini(cfg, system, messages, max_tokens, temperature):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{cfg['model']}:generateContent"
    headers = {"x-goog-api-key": cfg["api_key"]}
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [
            {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
            for m in messages
        ],
        "generationConfig": {"maxOutputTokens": max_tokens * 4, "temperature": temperature},
    }
    resp = _post(url, headers, payload)
    if resp.status_code != 200:
        raise LLMError(_error_message(resp))
    body = resp.json()
    candidates = body.get("candidates") or []
    if not candidates:
        raise LLMError("Gemini returned no answer (possibly blocked by safety filters)")
    parts = candidates[0].get("content", {}).get("parts", [])
    usage = body.get("usageMetadata", {})
    return "".join(p.get("text", "") for p in parts), {
        "prompt_tokens": usage.get("promptTokenCount", 0),
        "completion_tokens": usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0),
    }


_PROVIDERS = {"openai": _openai, "anthropic": _anthropic, "gemini": _gemini}


def call_llm(
    cfg: Dict[str, Any],
    system: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 450,
    temperature: float = 0.3,
) -> Tuple[str, Dict[str, int]]:
    """Return (answer_text, usage) where usage has prompt/completion/total token counts."""
    fn = _PROVIDERS.get(cfg["provider"])
    if not fn:
        raise LLMError(f"Unsupported provider: {cfg['provider']}")
    msgs = _normalize(messages)
    if not msgs:
        raise LLMError("No user message to send")
    text, usage = fn(cfg, system, msgs, max_tokens, temperature)
    usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
    return text.strip(), usage
