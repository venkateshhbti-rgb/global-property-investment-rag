"""Model choice for the app. Claude is the default when a key exists; OpenAI works too."""
import os
from typing import Any, Dict, List, Tuple

import query  # noqa: F401  (configures paths and puts the backend on sys.path)
from llm_client import call_llm  # backend module: plain-HTTP client for Anthropic, OpenAI and Gemini

_CANDIDATES = {
    "Claude": {"provider": "anthropic", "env": "ANTHROPIC_API_KEY", "model_env": "CLAUDE_MODEL", "default": "claude-sonnet-5-5"},
    "OpenAI": {"provider": "openai", "env": "OPENAI_API_KEY", "model_env": "OPENAI_CHAT_MODEL", "default": "gpt-4o-mini"},
}


def available_models() -> Dict[str, Dict[str, Any]]:
    """Models whose API key is present, keyed by a label such as 'Claude (claude-sonnet-5-5)'."""
    found = {}
    for name, c in _CANDIDATES.items():
        key = os.environ.get(c["env"], "").strip()
        if key:
            model = os.environ.get(c["model_env"], c["default"])
            found[f"{name} ({model})"] = {"provider": c["provider"], "model": model, "api_key": key, "name": name}
    return found


def complete(cfg: Dict[str, Any], system: str, messages: List[Dict[str, str]], max_tokens: int = 700) -> Tuple[str, Dict[str, int]]:
    return call_llm(cfg, system, messages, max_tokens=max_tokens, temperature=0.2)
