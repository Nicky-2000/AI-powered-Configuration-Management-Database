# app/main.py
from contextlib import asynccontextmanager
import os, asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import engine, Base
from .routers.ingest import router as ingest_router
from .routers.read import router as read_router
from .routers.ask import router as ask_router
from app.setup_logging import setup_logging
from app.nl.model_loader import load_model

setup_logging()

# Toggle via env: PRELOAD_BLOCKING=true|false
PRELOAD_BLOCKING = os.getenv("PRELOAD_BLOCKING", "true").lower() in ("1", "true", "yes")

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model_ready = False
    app.state.model_error = None

    async def _warmup():
        try:
            # non-blocking path uses a worker thread
            if PRELOAD_BLOCKING:
                load_model()
            else:
                await asyncio.to_thread(load_model)
            app.state.model_ready = True
        except Exception as e:
            app.state.model_error = str(e)
            app.state.model_ready = False

    if PRELOAD_BLOCKING:
        await _warmup()
    else:
        asyncio.create_task(_warmup())

    yield

app = FastAPI(title="AI-Ready CMDB (Step 1)", lifespan=lifespan)

@app.get("/healthz")
def health():
    return {
        "ok": True,
        "service": "cmdb",
        "version": 1,
        "model_ready": bool(getattr(app.state, "model_ready", False)),
        "model_error": getattr(app.state, "model_error", None),
    }

app.include_router(ingest_router)
app.include_router(read_router)
app.include_router(ask_router)
