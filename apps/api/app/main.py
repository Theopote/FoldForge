"""FoldForge FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import export, generate, health, process, upload

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered papercraft generation API for FoldForge / 纸模工坊",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated files from storage
app.mount(
    "/storage",
    StaticFiles(directory=str(settings.storage_root)),
    name="storage",
)

app.include_router(health.router)
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(generate.router, prefix="/api", tags=["generate"])
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
