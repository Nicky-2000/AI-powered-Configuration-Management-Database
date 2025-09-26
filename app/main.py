from contextlib import asynccontextmanager
import os, asyncio
from fastapi import FastAPI

from .db import engine, Base
from .routers.ingest import router as ingest_router
from .routers.read import router as read_router
from .routers.ask import router as ask_router
from app.setup_logging import setup_logging
from app.nl.model_loader import load_model

# --------------------------------------------------------------------
# App bootstrap
# --------------------------------------------------------------------
setup_logging() # Init Logging

# Flag to control whether model warmup blocks startup
#   PRELOAD_BLOCKING=true  -> wait for model to load before serving
#   PRELOAD_BLOCKING=false -> start server immediately and wait for model to load in background
PRELOAD_BLOCKING = os.getenv("PRELOAD_BLOCKING", "true").lower() in ("1", "true", "yes")

# Create database tables if they don’t exist.
Base.metadata.create_all(bind=engine)

# --------------------------------------------------------------------
# FastAPI application with lifespan hook
# --------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context runs once at startup and once at shutdown.
    Here we optionally warm up the NL->SQL model so the /ask endpoint
    is ready as soon as the service starts.
    """
    app.state.model_ready = False
    app.state.model_error = None

    async def _warmup():
        try:
            if PRELOAD_BLOCKING:
                # Blocking: run in current event loop (server waits for model)
                load_model()
            else:
                # Non-blocking: offload to a background thread
                await asyncio.to_thread(load_model)
            app.state.model_ready = True
        except Exception as e:
            # Store any load error so /healthz can report it
            app.state.model_error = str(e)
            app.state.model_ready = False

    # Decide whether to wait or fire-and-forget
    if PRELOAD_BLOCKING:
        await _warmup()
    else:
        asyncio.create_task(_warmup())

    # Hand control back to FastAPI to serve requests
    yield
    # No special shutdown logic needed

# Create the FastAPI app instance
app = FastAPI(title="AI-Ready CMDB (Step 1)", lifespan=lifespan)

# --------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------
@app.get("/healthz")
def health():
    """
    Simple health probe for monitoring.
    Returns:
      - ok: static True if the app is alive
      - model_ready: True when NL->SQL model finished loading
      - model_error: any load error message (None if healthy)
    """
    return {
        "ok": True,
        "service": "cmdb",
        "version": 1,
        "model_ready": bool(getattr(app.state, "model_ready", False)),
        "model_error": getattr(app.state, "model_error", None),
    }

# Register API routers:
app.include_router(ingest_router)
app.include_router(read_router)
app.include_router(ask_router)
