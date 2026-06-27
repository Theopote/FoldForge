"""Pydantic schemas for model upload and project data."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.unfold import CraftabilityScore, ProcessStats


class SourceType(str, Enum):
    UPLOAD_3D = "upload_3d"
    TEXT_TO_3D = "text_to_3d"
    IMAGE_TO_3D = "image_to_3d"


class ProjectStatus(str, Enum):
    CREATED = "created"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class PaperSize(str, Enum):
    A4 = "A4"
    A3 = "A3"
    LETTER = "Letter"


class Difficulty(str, Enum):
    EASY = "easy"
    STANDARD = "standard"
    ADVANCED = "advanced"


class Style(str, Enum):
    LOW_POLY = "low_poly"
    CUTE = "cute"
    GEOMETRIC = "geometric"


class ColorMode(str, Enum):
    COLOR = "color"
    LINE_ART = "line_art"


class ProjectSettings(BaseModel):
    """User-configurable papercraft generation settings."""

    paper_size: PaperSize = Field(alias="paperSize", default=PaperSize.A4)
    difficulty: Difficulty = Difficulty.STANDARD
    style: Style = Style.LOW_POLY
    target_height_mm: float = Field(alias="targetHeightMm", default=200.0)
    add_tabs: bool = Field(alias="addTabs", default=True)
    add_numbers: bool = Field(alias="addNumbers", default=True)
    add_fold_lines: bool = Field(alias="addFoldLines", default=True)
    add_cut_lines: bool = Field(alias="addCutLines", default=True)
    color_mode: ColorMode = Field(alias="colorMode", default=ColorMode.LINE_ART)

    model_config = {"populate_by_name": True}


class Project(BaseModel):
    """In-memory project record (MVP — no database yet)."""

    id: str
    name: str
    source_type: SourceType = Field(alias="sourceType")
    source_file_url: Optional[str] = Field(alias="sourceFileUrl", default=None)
    processed_model_url: Optional[str] = Field(alias="processedModelUrl", default=None)
    unfold_svg_url: Optional[str] = Field(alias="unfoldSvgUrl", default=None)
    unfold_pdf_url: Optional[str] = Field(alias="unfoldPdfUrl", default=None)
    unfold_zip_url: Optional[str] = Field(alias="unfoldZipUrl", default=None)
    status: ProjectStatus = ProjectStatus.CREATED
    settings: ProjectSettings = Field(default_factory=ProjectSettings)
    stats: Optional[ProcessStats] = None
    craftability: Optional[CraftabilityScore] = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}


class UploadModelResponse(BaseModel):
    project_id: str = Field(alias="projectId")
    source_file_url: str = Field(alias="sourceFileUrl")
    status: ProjectStatus

    model_config = {"populate_by_name": True}
