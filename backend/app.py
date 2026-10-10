import logging
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from llm_client import call_llm
from market_data import market_data
from rag_system import PropertyInvestmentRAG
from store import make_cache_key, store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.API_TITLE, version=settings.API_VERSION, debug=settings.DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_system: Optional[PropertyInvestmentRAG] = None


@app.on_event("startup")
async def startup_event():
    global rag_system
    logger.info("Initializing RAG system...")
    rag_system = PropertyInvestmentRAG()
    logger.info("✅ System is ready! Access at http://localhost:5173")


# ==================== Auth helpers ====================

def current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    token = authorization[7:] if authorization and authorization.startswith("Bearer ") else None
    user = store.user_for_token(token) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def admin_user(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def require_rag() -> PropertyInvestmentRAG:
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    return rag_system


# ==================== Models ====================

class LoginRequest(BaseModel):
    username: str
    password: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    user_profile: Optional[Dict[str, Any]] = None
    llm_id: Optional[str] = None


class ComparisonRequest(BaseModel):
    metric: str
    regions: List[str]
    user_profile: Optional[Dict[str, Any]] = None
    llm_id: Optional[str] = None


class NewUser(BaseModel):
    username: str
    password: str
    role: str = "user"


class NewLLM(BaseModel):
    name: str
    provider: str
    model: str
    api_key: str
    base_url: str = ""


class LLMUpdate(BaseModel):
    enabled: Optional[bool] = None
    model: Optional[str] = None


# ==================== Public ====================

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.API_TITLE, "version": settings.API_VERSION}


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    result = store.login(req.username, req.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return result


# ==================== Any signed-in user ====================

@app.get("/api/auth/me")
async def me(user: Dict[str, Any] = Depends(current_user)):
    return {"user": user, "usage": store.user_usage(user["username"])}


@app.post("/api/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        store.logout(authorization[7:])
    return {"status": "ok"}


@app.get("/api/llms")
async def available_llms(user: Dict[str, Any] = Depends(current_user)):
    return [{"id": l["id"], "name": l["name"], "model": l["model"]} for l in store.list_llms(include_disabled=False)]


@app.get("/api/system-stats")
async def get_system_stats(user: Dict[str, Any] = Depends(current_user)):
    return require_rag().get_system_stats()


def _finish(result: Dict[str, Any], user: Dict[str, Any], llm_cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if result.get("usage") and llm_cfg:
        store.record_usage(user["username"], llm_cfg["id"], result["usage"])
    result["user_usage"] = store.user_usage(user["username"])
    return result


@app.post("/api/chat")
async def chat_with_consultant(request: ChatRequest, user: Dict[str, Any] = Depends(current_user)):
    rag = require_rag()
    messages = [m.model_dump() for m in request.messages]
    if not any(m["role"] == "user" and m["content"].strip() for m in messages):
        raise HTTPException(status_code=400, detail="No user message found")
    llm_cfg = store.get_llm_config(request.llm_id)

    cache_key = None
    if llm_cfg:
        user_turns = [m["content"] for m in messages[-8:] if m["role"] == "user"]
        cache_key = make_cache_key("chat", user_turns, request.user_profile, llm_cfg, f"{rag.data_version}:{market_data.stamp()}:{rag.retrieval_tag}")
        saved = store.cache_get(cache_key)
        if saved:
            return {
                "message": {"role": "assistant", "content": saved["answer"]},
                "sources": saved["sources"],
                "success": True,
                "usage": None,
                "user_usage": store.user_usage(user["username"]),
                "llm": saved["llm"],
                "clarifying_questions": saved.get("clarifying_questions"),
                "cached": True,
            }

    try:
        result = rag.chat(messages, request.user_profile, llm_cfg)
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing chat: {e}")
    result = _finish(result, user, llm_cfg)
    if cache_key and result["success"] and result["usage"]:
        store.cache_put(cache_key, {
            "answer": result["answer"], "sources": result["sources"], "llm": result["llm"],
            "clarifying_questions": result.get("clarifying_questions"),
        })
    return {
        "message": {"role": "assistant", "content": result["answer"]},
        "sources": result["sources"],
        "success": result["success"],
        "usage": result["usage"],
        "user_usage": result["user_usage"],
        "llm": result["llm"],
        "clarifying_questions": result.get("clarifying_questions"),
        "cached": False,
    }


@app.post("/api/compare-regions")
async def compare_regions(request: ComparisonRequest, user: Dict[str, Any] = Depends(current_user)):
    rag = require_rag()
    if not request.metric.strip() or not request.regions:
        raise HTTPException(status_code=400, detail="Metric and regions are required")
    llm_cfg = store.get_llm_config(request.llm_id)

    cache_key = None
    if llm_cfg:
        cache_key = make_cache_key(
            "compare", [request.metric] + sorted(request.regions), request.user_profile, llm_cfg, f"{rag.data_version}:{market_data.stamp()}:{rag.retrieval_tag}"
        )
        saved = store.cache_get(cache_key)
        if saved:
            return {
                "answer": saved["answer"], "sources": saved["sources"], "success": True,
                "usage": None, "llm": saved["llm"], "cached": True,
                "user_usage": store.user_usage(user["username"]),
            }

    try:
        result = rag.compare_regions(request.metric, request.regions, request.user_profile, llm_cfg)
    except Exception as e:
        logger.error(f"Error comparing regions: {e}")
        raise HTTPException(status_code=500, detail=f"Error comparing regions: {e}")
    result = _finish(result, user, llm_cfg)
    if cache_key and result["success"] and result["usage"]:
        store.cache_put(cache_key, {"answer": result["answer"], "sources": result["sources"], "llm": result["llm"]})
    result["cached"] = False
    return result


# ==================== Admin only ====================

@app.post("/api/reload-documents")
async def reload_documents(user: Dict[str, Any] = Depends(admin_user)):
    try:
        stats = require_rag().reload_documents()
        cleared = store.cache_clear()
        return {"status": "success",
                "message": f"Documents reloaded. Cleared {cleared} saved answers so they reflect the new data.",
                "stats": stats}
    except Exception as e:
        logger.error(f"Error reloading documents: {e}")
        return {"status": "error", "message": f"Error reloading documents: {e}"}


@app.get("/api/admin/cache")
async def cache_info(user: Dict[str, Any] = Depends(admin_user)):
    return {"saved_answers": store.cache_size()}


@app.delete("/api/admin/cache")
async def clear_cache(user: Dict[str, Any] = Depends(admin_user)):
    return {"cleared": store.cache_clear()}


@app.get("/api/admin/retrieval")
async def retrieval_status(user: Dict[str, Any] = Depends(admin_user)):
    return require_rag().retrieval_status()


@app.get("/api/admin/market-data")
async def get_market_data(user: Dict[str, Any] = Depends(admin_user)):
    rag = require_rag()
    return {"markets": market_data.snapshot(rag.regions), "stamp": market_data.stamp()}


@app.post("/api/admin/market-data/refresh")
async def refresh_market_data(user: Dict[str, Any] = Depends(admin_user)):
    rag = require_rag()
    await run_in_threadpool(market_data.refresh, rag.regions, True)
    return {"markets": market_data.snapshot(rag.regions), "stamp": market_data.stamp()}


@app.get("/api/admin/users")
async def list_users(user: Dict[str, Any] = Depends(admin_user)):
    return store.list_users()


@app.post("/api/admin/users")
async def create_user(req: NewUser, user: Dict[str, Any] = Depends(admin_user)):
    try:
        return store.add_user(req.username, req.password, req.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/admin/users/{username}")
async def remove_user(username: str, user: Dict[str, Any] = Depends(admin_user)):
    if username == user["username"]:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    try:
        store.delete_user(username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}


@app.get("/api/admin/llms")
async def list_llms(user: Dict[str, Any] = Depends(admin_user)):
    return store.list_llms()


@app.post("/api/admin/llms")
async def create_llm(req: NewLLM, user: Dict[str, Any] = Depends(admin_user)):
    try:
        return store.add_llm(req.name, req.provider, req.model, req.api_key, req.base_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/api/admin/llms/{llm_id}")
async def update_llm(llm_id: str, req: LLMUpdate, user: Dict[str, Any] = Depends(admin_user)):
    try:
        if req.enabled is not None:
            store.set_llm_enabled(llm_id, req.enabled)
        if req.model is not None:
            store.set_llm_model(llm_id, req.model)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "ok"}


@app.delete("/api/admin/llms/{llm_id}")
async def remove_llm(llm_id: str, user: Dict[str, Any] = Depends(admin_user)):
    try:
        store.delete_llm(llm_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "ok"}


@app.post("/api/admin/llms/{llm_id}/test")
async def test_llm(llm_id: str, user: Dict[str, Any] = Depends(admin_user)):
    cfg = store.get_llm_config(llm_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="LLM not found or disabled")
    try:
        _, usage = call_llm(cfg, "Reply with the single word: ok", [{"role": "user", "content": "ping"}], max_tokens=16)
    except Exception as e:
        return {"ok": False, "message": str(e)}
    return {"ok": True, "message": f"Connected ({usage['total_tokens']} tokens used)"}


@app.get("/")
async def root():
    return {"service": settings.API_TITLE, "version": settings.API_VERSION, "status": "running", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
