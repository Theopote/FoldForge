"""FoldForge API configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "FoldForge API"
    app_version: str = "0.1.0"
    debug: bool = True

    # Paths relative to monorepo root
    storage_root: Path = Path(__file__).resolve().parents[3] / "storage"
    database_path: Path = storage_root / "foldforge.db"
    uploads_dir: Path = storage_root / "uploads"
    processed_dir: Path = storage_root / "processed"
    exports_dir: Path = storage_root / "exports"

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    max_upload_size_mb: int = 50
    max_image_size_mb: int = 10
    # Official MVP formats (Trimesh + Three.js preview)
    supported_extensions: set[str] = {".obj", ".stl", ".glb", ".gltf"}
    # Accepted by Trimesh in some builds but unreliable — not offered in UI/API MVP
    experimental_extensions: set[str] = {".fbx"}
    allowed_image_extensions: set[str] = {".jpg", ".jpeg", ".png", ".webp"}

    # AI generation (Phase 2+)
    ai_provider: str = "auto"  # auto | mock | meshy | triposr | replicate
    ai_async_for_mock: bool = False
    replicate_api_token: str | None = None
    replicate_text_model: str = ""
    replicate_image_model: str = ""
    # TripoSR via Replicate (image-to-3D). Example: camenduru/tripo-sr version hash
    triposr_replicate_version: str = ""
    # Meshy API — https://docs.meshy.ai
    meshy_api_key: str | None = None
    meshy_poll_interval_sec: float = 3.0
    meshy_poll_timeout_sec: float = 600.0

    # Papercraft quality
    block_export_on_unfold_overlap: bool = True


settings = Settings()

# Ensure storage directories exist at startup
for directory in (settings.uploads_dir, settings.processed_dir, settings.exports_dir):
    directory.mkdir(parents=True, exist_ok=True)
