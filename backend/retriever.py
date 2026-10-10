"""Hybrid retrieval: keyword (TF-IDF) + semantic embeddings, fused with RRF, then cross-encoder reranking.

Embeddings are built in a background thread and cached on disk by chunk hash, so the app is usable immediately
(keyword mode), interrupted runs resume where they stopped, and unchanged documents are never re-embedded.
"""
# onnxruntime must be imported BEFORE scikit-learn: the reverse order segfaults on Windows (conflicting OpenMP runtimes).
try:
    import onnxruntime  # noqa: F401
except ImportError:
    pass

import hashlib
import os
import threading
import time
from collections import Counter
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

CANDIDATES = 30        # per retriever, before fusion
RERANK_POOL = 15       # fused candidates sent to the reranker
RRF_K = 60


def _normalize(arr: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(arr, axis=-1, keepdims=True)
    return (arr / np.clip(norms, 1e-9, None)).astype(np.float32)


class LocalEmbedder:
    """fastembed (ONNX) embeddings that run on this machine. Free and private, but slow on a laptop CPU."""

    def __init__(self, model: str, cache_dir: str):
        from fastembed import TextEmbedding
        self.tag = f"local_{model.replace('/', '_')}"
        self.lock = threading.Lock()
        self.model = TextEmbedding(model, cache_dir=cache_dir, threads=os.cpu_count())

    def embed_documents(self, texts: List[str]) -> np.ndarray:
        with self.lock:
            return _normalize(np.array(list(self.model.embed(texts, batch_size=32)), dtype=np.float32))

    def embed_query(self, text: str) -> np.ndarray:
        with self.lock:
            return _normalize(np.array(list(self.model.query_embed(text)), dtype=np.float32))[0]


class OpenAIEmbedder:
    """OpenAI embeddings over plain HTTP, with backoff on rate limits."""

    def __init__(self, api_key: str, model: str, dimensions: int):
        self.api_key, self.model, self.dimensions = api_key, model, dimensions
        self.tag = f"openai_{model}_{dimensions}"

    def _call(self, texts: List[str]) -> np.ndarray:
        payload: Dict[str, Any] = {"model": self.model, "input": [t[:6000] for t in texts]}
        if self.dimensions and "text-embedding-3" in self.model:
            payload["dimensions"] = self.dimensions
        for attempt in range(8):
            try:
                resp = requests.post("https://api.openai.com/v1/embeddings", json=payload, timeout=60,
                                     headers={"Authorization": f"Bearer {self.api_key}"})
            except requests.RequestException:
                time.sleep(min(2 ** attempt, 30))
                continue
            if resp.status_code == 200:
                rows = sorted(resp.json()["data"], key=lambda r: r["index"])
                return np.array([r["embedding"] for r in rows], dtype=np.float32)
            if resp.status_code == 429 and "insufficient_quota" not in resp.text:
                wait = float(resp.headers.get("retry-after", 0) or 0) or min(2 ** attempt * 2, 60)
                time.sleep(wait)
                continue
            try:
                message = resp.json()["error"]["message"]
            except (ValueError, KeyError):
                message = resp.text[:200]
            raise RuntimeError(f"OpenAI embeddings error {resp.status_code}: {message}")
        raise RuntimeError("OpenAI embeddings: too many retries")

    def embed_documents(self, texts: List[str]) -> np.ndarray:
        return _normalize(self._call(texts))

    def embed_query(self, text: str) -> np.ndarray:
        return _normalize(self._call([text]))[0]


class HybridRetriever:
    def __init__(
        self,
        texts: List[str],
        region_indices: Dict[str, np.ndarray],
        embedder_factory: Optional[Callable[[], Any]],
        cache_dir: str,
        reranker_factory: Optional[Callable[[], Any]],
    ):
        self.texts = texts
        self.region_indices = region_indices
        self.embedder_factory = embedder_factory
        self.reranker_factory = reranker_factory
        self.cache_dir = cache_dir
        self.embedder = None
        self.reranker = None
        self.rerank_lock = threading.Lock()
        self.vecs: Optional[np.ndarray] = None
        self.status: Dict[str, Any] = {
            "provider": None, "embedded": 0, "total": len(texts), "ready": False,
            "error": None, "reranker": "off" if reranker_factory is None else "loading",
        }
        self.tfidf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=200000, sublinear_tf=True)
        self.matrix = self.tfidf.fit_transform(texts)

    # ---------- background work ----------
    def start_background(self):
        if self.embedder_factory:
            threading.Thread(target=self._build_dense, daemon=True).start()
        if self.reranker_factory:
            threading.Thread(target=self._load_reranker, daemon=True).start()

    def _load_reranker(self):
        try:
            self.reranker = self.reranker_factory()
            self.status["reranker"] = "ready"
        except Exception as e:
            self.status["reranker"] = "error"
            self.status["error"] = f"Reranker unavailable: {e}"

    def _build_dense(self):
        try:
            self.embedder = self.embedder_factory()
            self.status["provider"] = self.embedder.tag
            keys = [hashlib.md5(t.encode("utf-8")).hexdigest() for t in self.texts]
            counts = Counter(keys)
            os.makedirs(self.cache_dir, exist_ok=True)
            path = os.path.join(self.cache_dir, f"{self.embedder.tag}.npz")

            store: Dict[str, np.ndarray] = {}
            if os.path.exists(path):
                with np.load(path, allow_pickle=False) as data:  # close the handle: Windows blocks overwriting an open file
                    store = dict(zip(data["keys"].tolist(), list(data["vecs"])))

            embedded = sum(counts[k] for k in counts if k in store)
            self.status["embedded"] = embedded
            first_text = {}
            for k, t in zip(keys, self.texts):
                first_text.setdefault(k, t)
            missing = [k for k in counts if k not in store]

            batch, last_save = 64, time.time()
            for start in range(0, len(missing), batch):
                chunk_keys = missing[start:start + batch]
                vecs = self.embedder.embed_documents([first_text[k] for k in chunk_keys])
                for k, v in zip(chunk_keys, vecs):
                    store[k] = v
                embedded += sum(counts[k] for k in chunk_keys)
                self.status["embedded"] = embedded
                if time.time() - last_save > 45:
                    self._save(path, store)
                    last_save = time.time()
            if missing:
                self._save(path, store)

            self.vecs = np.stack([store[k] for k in keys])
            self.status.update(embedded=len(keys), ready=True)
        except Exception as e:
            self.status["error"] = f"Embeddings unavailable ({e}). Using keyword search."

    @staticmethod
    def _save(path: str, store: Dict[str, np.ndarray]):
        """Checkpoint to disk. A failed save must never abort the build; the next checkpoint retries."""
        try:
            keys = np.array(list(store.keys()))
            tmp = path + ".tmp.npz"
            np.savez(tmp, keys=keys, vecs=np.stack(list(store.values())))
            os.replace(tmp, path)
        except OSError as e:
            print(f"[retriever] checkpoint not saved, will retry: {e}")

    # ---------- search ----------
    @property
    def mode(self) -> str:
        if self.vecs is not None and self.reranker is not None:
            return "hybrid+rerank"
        if self.vecs is not None:
            return "hybrid"
        if self.reranker is not None:
            return "keyword+rerank"
        return "keyword"

    def _top(self, scores: np.ndarray, idx: Optional[np.ndarray], n: int, positive_only: bool) -> List[int]:
        order = idx[np.argsort(scores[idx])[::-1][:n]] if idx is not None else np.argsort(scores)[::-1][:n]
        return [int(i) for i in order if not positive_only or scores[i] > 0]

    def search(self, query: str, k: int = 5, region: Optional[str] = None, rerank_query: Optional[str] = None) -> List[int]:
        if not query.strip():
            return []
        idx = None
        if region is not None:
            idx = self.region_indices.get(region)
            if idx is None or len(idx) == 0:
                return []

        lists = [self._top(linear_kernel(self.tfidf.transform([query]), self.matrix)[0], idx, CANDIDATES, True)]
        if self.vecs is not None:
            try:
                q = self.embedder.embed_query(query)
                lists.append(self._top(self.vecs @ q, idx, CANDIDATES, False))
            except Exception:
                pass

        fused: Dict[int, float] = {}
        for ranking in lists:
            for rank, i in enumerate(ranking):
                fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rank + 1)
        pool = sorted(fused, key=fused.get, reverse=True)[:RERANK_POOL]

        if self.reranker is not None and len(pool) > 1:
            try:
                with self.rerank_lock:
                    scores = list(self.reranker.rerank(rerank_query or query, [self.texts[i][:1000] for i in pool]))
                pool = [i for _, i in sorted(zip(scores, pool), key=lambda p: p[0], reverse=True)]
            except Exception:
                pass
        return pool[:k]
