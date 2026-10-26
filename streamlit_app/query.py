"""Bootstraps the backend's engine for the Streamlit app.

The app reuses the backend modules (retriever, RAG, store, market data) directly, in the same process, so it behaves
exactly like the FastAPI + React app without needing that server.
"""
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent
BACKEND = ROOT / "backend"
STATE = APP_DIR / ".state"


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


def fingerprint(rag: Optional[PropertyInvestmentRAG] = None) -> str:
    """Changes when the documents, live data or search mode change, so saved answers don't go stale."""
    rag = rag or get_rag()
    return f"{rag.data_version}:{market_data.stamp()}:{rag.retrieval_tag}"


def countries() -> List[str]:
    return get_rag().regions


def status() -> Dict[str, Any]:
    return get_rag().retrieval_status()
