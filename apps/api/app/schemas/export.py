"""Schemas for export endpoints."""

from pydantic import BaseModel, Field


class ExportInfo(BaseModel):
    project_id: str = Field(alias="projectId")
    format: str
    download_url: str = Field(alias="downloadUrl")

    model_config = {"populate_by_name": True}
