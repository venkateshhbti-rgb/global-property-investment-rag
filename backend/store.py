import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from config import settings

_lock = threading.RLock()
TOKEN_TTL_SECONDS = 7 * 24 * 3600
CACHE_VERSION = "v11"  # bump when prompts change so old saved answers are not reused
CACHE_MAX_ENTRIES = 500


def make_cache_key(kind, texts, profile, llm_cfg, data_version: str = "") -> str:
    """Stable key from the normalized user turns, investor profile and model."""
    norm = "||".join(" ".join(re.sub(r"[^a-z0-9$ ]+", " ", t.lower()).split()) for t in texts)
    p = profile or {}
    parts = [CACHE_VERSION, data_version, kind, norm, str(p.get("budget") or ""), str(p.get("type") or ""),
             str(p.get("risk_profile") or ""), f"{llm_cfg['provider']}:{llm_cfg['model']}"]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def _empty_usage() -> Dict[str, int]:
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "requests": 0}


def _hash_password(password: str, salt: Optional[str] = None) -> Dict[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
    return {"salt": salt, "hash": digest}


def _verify_password(password: str, salt: str, expected: str) -> bool:
    candidate = _hash_password(password, salt)["hash"]
    return hmac.compare_digest(candidate, expected)


class Store:
    """JSON-file store for users, sessions, LLM providers and token usage."""

    def __init__(self, path: str):
        self.path = path
        self.data: Dict[str, Any] = {"users": {}, "sessions": {}, "llms": [], "usage": {"users": {}, "llms": {}}, "cache": {}}
        self._load()
        self._seed()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.data.update(json.load(f))

    def _save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
        os.replace(tmp, self.path)

    def _seed(self):
        with _lock:
            if not self.data["users"]:
                password = settings.ADMIN_PASSWORD or secrets.token_urlsafe(9)
                self.add_user(settings.ADMIN_USERNAME, password, "admin")
                if settings.ADMIN_PASSWORD:
                    print(f"[auth] Created admin user '{settings.ADMIN_USERNAME}' with the ADMIN_PASSWORD from .env.")
                else:
                    print(f"[auth] Created admin user '{settings.ADMIN_USERNAME}' with a generated password: {password}")
                    print("[auth] Save it now, it is not shown again. Or set ADMIN_PASSWORD in backend/.env before first run.")
            if not self.data["llms"] and settings.OPENAI_API_KEY:
                self.add_llm("OpenAI (from .env)", "openai", settings.OPENAI_MODEL, settings.OPENAI_API_KEY)

    # ---------- users ----------
    def add_user(self, username: str, password: str, role: str = "user") -> Dict[str, Any]:
        username = username.strip()
        with _lock:
            if not username or len(password) < 6:
                raise ValueError("Username required and password must be at least 6 characters")
            if role not in ("admin", "user"):
                raise ValueError("Role must be 'admin' or 'user'")
            if username.lower() in {u.lower() for u in self.data["users"]}:
                raise ValueError("Username already exists")
            pw = _hash_password(password)
            self.data["users"][username] = {"role": role, "created": int(time.time()), **pw}
            self._save()
            return self.public_user(username)

    def public_user(self, username: str) -> Dict[str, Any]:
        u = self.data["users"][username]
        return {"username": username, "role": u["role"], "created": u["created"]}

    def list_users(self) -> List[Dict[str, Any]]:
        with _lock:
            return [
                {**self.public_user(name), "usage": self.data["usage"]["users"].get(name, _empty_usage())}
                for name in self.data["users"]
            ]

    def delete_user(self, username: str):
        with _lock:
            if username not in self.data["users"]:
                raise ValueError("User not found")
            admins = [n for n, u in self.data["users"].items() if u["role"] == "admin"]
            if self.data["users"][username]["role"] == "admin" and len(admins) <= 1:
                raise ValueError("Cannot delete the last admin")
            del self.data["users"][username]
            self.data["sessions"] = {t: s for t, s in self.data["sessions"].items() if s["username"] != username}
            self._save()

    def login(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        with _lock:
            match = next((n for n in self.data["users"] if n.lower() == username.strip().lower()), None)
            if not match:
                _hash_password(password)  # keep timing similar
                return None
            u = self.data["users"][match]
            if not _verify_password(password, u["salt"], u["hash"]):
                return None
            token = secrets.token_urlsafe(32)
            self.data["sessions"][token] = {"username": match, "created": int(time.time())}
            self._save()
            return {"token": token, "user": self.public_user(match)}

    def user_for_token(self, token: str) -> Optional[Dict[str, Any]]:
        with _lock:
            s = self.data["sessions"].get(token)
            if not s:
                return None
            if time.time() - s["created"] > TOKEN_TTL_SECONDS or s["username"] not in self.data["users"]:
                del self.data["sessions"][token]
                self._save()
                return None
            return self.public_user(s["username"])

    def logout(self, token: str):
        with _lock:
            if self.data["sessions"].pop(token, None):
                self._save()

    # ---------- LLM providers ----------
    @staticmethod
    def _mask(key: str) -> str:
        return ("•" * 8 + key[-4:]) if len(key) > 4 else "••••"

    def _public_llm(self, llm: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": llm["id"], "name": llm["name"], "provider": llm["provider"],
            "model": llm["model"], "base_url": llm.get("base_url", ""),
            "enabled": llm["enabled"], "api_key_masked": self._mask(llm["api_key"]),
            "usage": self.data["usage"]["llms"].get(llm["id"], _empty_usage()),
        }

    def add_llm(self, name: str, provider: str, model: str, api_key: str, base_url: str = "") -> Dict[str, Any]:
        if provider not in ("openai", "anthropic", "gemini"):
            raise ValueError("Provider must be openai, anthropic or gemini")
        if not (name.strip() and model.strip() and api_key.strip()):
            raise ValueError("Name, model and API key are required")
        with _lock:
            llm = {
                "id": uuid.uuid4().hex[:8], "name": name.strip(), "provider": provider,
                "model": model.strip(), "api_key": api_key.strip(),
                "base_url": base_url.strip().rstrip("/"), "enabled": True,
            }
            self.data["llms"].append(llm)
            self._save()
            return self._public_llm(llm)

    def list_llms(self, include_disabled: bool = True) -> List[Dict[str, Any]]:
        with _lock:
            return [self._public_llm(l) for l in self.data["llms"] if include_disabled or l["enabled"]]

    def get_llm_config(self, llm_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Full config including the secret key. Server-side use only."""
        with _lock:
            enabled = [l for l in self.data["llms"] if l["enabled"]]
            if llm_id:
                return next((l for l in enabled if l["id"] == llm_id), None)
            return enabled[0] if enabled else None

    def set_llm_enabled(self, llm_id: str, enabled: bool):
        with _lock:
            llm = next((l for l in self.data["llms"] if l["id"] == llm_id), None)
            if not llm:
                raise ValueError("LLM not found")
            llm["enabled"] = enabled
            self._save()

    def openai_key(self) -> str:
        """API key of the first enabled official-OpenAI provider (used for embeddings), or empty."""
        with _lock:
            for l in self.data["llms"]:
                if l["enabled"] and l["provider"] == "openai" and not l.get("base_url"):
                    return l["api_key"]
        return ""

    def set_llm_model(self, llm_id: str, model: str):
        model = model.strip()
        if not model:
            raise ValueError("Model name is required")
        with _lock:
            llm = next((l for l in self.data["llms"] if l["id"] == llm_id), None)
            if not llm:
                raise ValueError("LLM not found")
            llm["model"] = model
            self._save()

    def delete_llm(self, llm_id: str):
        with _lock:
            before = len(self.data["llms"])
            self.data["llms"] = [l for l in self.data["llms"] if l["id"] != llm_id]
            if len(self.data["llms"]) == before:
                raise ValueError("LLM not found")
            self._save()

    # ---------- usage ----------
    def record_usage(self, username: str, llm_id: str, usage: Dict[str, int]):
        with _lock:
            for bucket, key in (("users", username), ("llms", llm_id)):
                entry = self.data["usage"][bucket].setdefault(key, _empty_usage())
                entry["prompt_tokens"] += usage.get("prompt_tokens", 0)
                entry["completion_tokens"] += usage.get("completion_tokens", 0)
                entry["total_tokens"] += usage.get("total_tokens", 0)
                entry["requests"] += 1
            self._save()

    def user_usage(self, username: str) -> Dict[str, int]:
        with _lock:
            return dict(self.data["usage"]["users"].get(username, _empty_usage()))


    # ---------- saved answers ----------
    def cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        with _lock:
            entry = self.data["cache"].get(key)
            return dict(entry) if entry else None

    def cache_put(self, key: str, payload: Dict[str, Any]):
        with _lock:
            cache = self.data["cache"]
            cache[key] = {**payload, "created": int(time.time())}
            if len(cache) > CACHE_MAX_ENTRIES:
                oldest = sorted(cache, key=lambda k: cache[k]["created"])[: len(cache) - CACHE_MAX_ENTRIES]
                for k in oldest:
                    del cache[k]
            self._save()

    def cache_clear(self) -> int:
        with _lock:
            count = len(self.data["cache"])
            self.data["cache"] = {}
            self._save()
            return count

    def cache_size(self) -> int:
        with _lock:
            return len(self.data["cache"])


store = Store(settings.DATA_STORE_PATH)
