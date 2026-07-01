"""FoldForge API configuration."""

from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
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
    cache_dir: Path = storage_root / "cache"

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # API authentication — set api_key to protect /api and /storage routes
    api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("FOLDFORGE_API_KEY", "API_KEY"),
    )
    require_api_auth: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "FOLDFORGE_REQUIRE_API_AUTH",
            "REQUIRE_API_AUTH",
        ),
    )

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
    ai_allow_provider_fallback: bool = False
    replicate_api_token: str | None = None
    replicate_text_model: str = ""
    replicate_image_model: str = ""
    # TripoSR via Replicate (image-to-3D). Example: camenduru/tripo-sr version hash
    triposr_replicate_version: str = ""
    # Meshy API — https://docs.meshy.ai
    meshy_api_key: str | None = None
    meshy_poll_interval_sec: float = 3.0
    meshy_poll_timeout_sec: float = 600.0

    # Papercraft job worker identity and lease (multi-instance prep)
    process_worker_id: str | None = None
    process_job_lease_sec: int = 600
    process_job_lease_watch_sec: float = 60.0

    # Papercraft quality — strict (default) vs warning overlap policy; see unfold_repair
    block_export_on_unfold_overlap: bool = True

    # Storage retention — delete unreferenced files under uploads/processed/exports
    storage_cleanup_enabled: bool = True
    storage_cleanup_interval_sec: float = 3600.0
    storage_file_ttl_days: int = 30

    # Layout — exact NFP nesting is O(n²) and slow for large models
    layout_nfp_max_pieces: int = Field(
        default=24,
        validation_alias=AliasChoices(
            "LAYOUT_NFP_MAX_PIECES",
            "FOLDFORGE_LAYOUT_NFP_MAX_PIECES",
        ),
    )
    layout_nfp_max_stationary: int = Field(
        default=12,
        validation_alias=AliasChoices(
            "LAYOUT_NFP_MAX_STATIONARY",
            "FOLDFORGE_LAYOUT_NFP_MAX_STATIONARY",
        ),
    )

    material_cache_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "MATERIAL_CACHE_ENABLED",
            "FOLDFORGE_MATERIAL_CACHE_ENABLED",
        ),
    )

    # Paid AI generation — per API key (or client IP when auth is off)
    ai_generation_rate_limit_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "AI_GENERATION_RATE_LIMIT_ENABLED",
            "FOLDFORGE_AI_GENERATION_RATE_LIMIT_ENABLED",
        ),
    )
    ai_generation_rate_limit_per_hour: int = Field(
        default=12,
        validation_alias=AliasChoices(
            "AI_GENERATION_RATE_LIMIT_PER_HOUR",
            "FOLDFORGE_AI_GENERATION_RATE_LIMIT_PER_HOUR",
        ),
    )
    ai_generation_rate_limit_burst: int = Field(
        default=3,
        validation_alias=AliasChoices(
            "AI_GENERATION_RATE_LIMIT_BURST",
            "FOLDFORGE_AI_GENERATION_RATE_LIMIT_BURST",
        ),
    )

    @model_validator(mode="after")
    def validate_auth_settings(self):
        if self.require_api_auth and not self.api_key:
            raise ValueError("require_api_auth is enabled but api_key is not configured")
        return self


settings = Settings()

# Ensure storage directories exist at startup
for directory in (
    settings.uploads_dir,
    settings.processed_dir,
    settings.exports_dir,
    settings.cache_dir,
):
    directory.mkdir(parents=True, exist_ok=True)
