"""Retrieval for the Streamlit app.

Reuses the backend's hybrid retriever (keyword + semantic + reranker), so there is no second index to maintain.
`search()` returns (text, metadata) pairs instead of printing them.
"""
import datetime as dt
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent
BACKEND = ROOT / "backend"
STATE = APP_DIR / ".state"
ALL_MARKETS = "All markets"


def _configure() -> None:
    """Point the backend's settings at absolute paths. Must run before the backend config is imported."""
    env_file = BACKEND / ".env"
    if env_file.exists():
        from dotenv import dotenv_values
        for key, value in dotenv_values(env_file).items():
            if value is not None:
                os.environ.setdefault(key, value)

    STATE.mkdir(exist_ok=True)
    os.environ.setdefault("DATA_BASE_PATH", str(ROOT / "data"))
    os.environ.setdefault("DATA_STORE_PATH", str(STATE / "store.json"))
    os.environ.setdefault("MARKET_CACHE_PATH", str(STATE / "market_cache.json"))
    # Reuse the backend's embeddings and downloaded models when they exist, so nothing is embedded twice.
    os.environ.setdefault("EMBEDDINGS_DIR", str((BACKEND if (BACKEND / "embeddings").exists() else STATE) / "embeddings"))
    os.environ.setdefault("MODELS_DIR", str((BACKEND if (BACKEND / "models").exists() else STATE) / "models"))


_configure()
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# onnxruntime must load before scikit-learn on Windows (see backend/retriever.py).
try:
    import onnxruntime  # noqa: F401
except ImportError:
    pass

from market_data import market_data  # noqa: E402
from rag_system import PropertyInvestmentRAG  # noqa: E402

_rag: Optional[PropertyInvestmentRAG] = None


def get_rag() -> PropertyInvestmentRAG:
    global _rag
    if _rag is None:
        _rag = PropertyInvestmentRAG()
    return _rag


def countries() -> List[str]:
    return get_rag().regions


def _file_date(source: Optional[str]) -> Optional[str]:
    """Last-modified date of the source file. The documents carry no effective date, so this is the closest signal."""
    try:
        return dt.datetime.fromtimestamp(os.path.getmtime(source)).strftime("%Y-%m-%d") if source else None
    except OSError:
        return None


def search(query: str, country: Optional[str] = None, k: int = 5) -> List[Tuple[str, Dict[str, Any]]]:
    """Return [(text, metadata), ...] for the best passages, optionally restricted to one country."""
    rag = get_rag()
    region = None if country in (None, "", ALL_MARKETS) else country
    topic = rag._without_regions(query) if region else query
    hits = []
    for doc in rag.retrieve(topic, k=k, region=region):
        m = doc.metadata
        hits.append((doc.page_content, {
            "source_file": m.get("file_name", "unknown"),
            "page": m.get("page_number"),
            "country": m.get("region"),
            "doc_type": m.get("document_type"),
            "file_date": _file_date(m.get("source")),
        }))
    return hits


def live_context(country: Optional[str], hits: List[Tuple[str, Dict[str, Any]]]) -> str:
    """Dated World Bank / BIS / FX figures for the selected country, or for the countries the hits came from."""
    if country in (None, "", ALL_MARKETS):
        names = []
        for _, meta in hits:
            if meta["country"] and meta["country"] not in names:
                names.append(meta["country"])
        names = names[:3]
    else:
        names = [country]
    return market_data.context_for(names)[0]


def cache_fingerprint() -> str:
    """Changes when the documents, live data or retrieval mode change, so saved answers don't go stale."""
    rag = get_rag()
    return f"{rag.data_version}:{market_data.stamp()}:{rag.retrieval_tag}"


def status() -> Dict[str, Any]:
    return get_rag().retrieval_status()
