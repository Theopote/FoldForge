"""FoldForge FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.middleware.api_auth import APIKeyMiddleware
from app.routers import export, generate, health, jobs, process, upload
from app.services.ai.generation_queue import generation_queue
from app.services.process_queue import process_queue
from app.services.storage_cleanup import storage_cleanup_task


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background workers on startup."""
    await generation_queue.recover_pending_jobs()
    await process_queue.recover_pending_jobs()
    await generation_queue.start()
    await process_queue.start()
    await storage_cleanup_task.start()
    yield
    await storage_cleanup_task.stop()
    await process_queue.stop()
    await generation_queue.stop()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered papercraft generation API for FoldForge / 纸模工坊",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(APIKeyMiddleware)

# Serve generated files from storage
app.mount(
    "/storage",
    StaticFiles(directory=str(settings.storage_root)),
    name="storage",
)

app.include_router(health.router)
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(generate.router, prefix="/api", tags=["generate"])
app.include_router(jobs.router, prefix="/api", tags=["jobs"])
app.include_router(process.router, prefix="/api", tags=["process"])
app.include_router(export.router, prefix="/api", tags=["export"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API info."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
