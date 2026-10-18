"""FastAPI Backend Server for Project Jarvis.

Exposes REST and WebSocket endpoints for UI telemetry, status, and communication.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
from typing import Any, AsyncGenerator, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from memory.db import check_db_health, init_db

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager to handle startup and shutdown events."""
    try:
        await init_db()
    except Exception as exc:
        print(f"[ERROR] Failed to initialize SQLite database during startup: {exc}")
        raise exc
    yield


app = FastAPI(
    title="Jarvis AI Assistant Backend",
    description="REST and WebSocket backend for Jarvis AI Assistant",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for local UI development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """Healthcheck endpoint reporting server and database connection status."""
    try:
        is_connected = await check_db_health()
        if not is_connected:
            # Attempt to re-initialize if not yet ready
            await init_db()
            is_connected = await check_db_health()

        if is_connected:
            return {"status": "healthy", "db": "connected"}

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "degraded", "db": "disconnected"},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(exc)}",
        ) from exc


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("SERVER_PORT", "8000"))
    uvicorn.run("ui.server:app", host=host, port=port, reload=True)
