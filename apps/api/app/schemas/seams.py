"""API schemas for seam editing."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SeamToggleRequest(BaseModel):
    mesh_edge: str = Field(alias="meshEdge")

    model_config = {"populate_by_name": True}


class UpdateProjectSeamsRequest(BaseModel):
    toggle: SeamToggleRequest | None = None
    seams: list[str] | None = None

    @model_validator(mode="after")
    def require_one_action(self) -> UpdateProjectSeamsRequest:
        if self.toggle is None and self.seams is None:
            raise ValueError("Provide either toggle or seams.")
        if self.toggle is not None and self.seams is not None:
            raise ValueError("Provide only one of toggle or seams.")
        return self


class UpdateProjectSeamsResponse(BaseModel):
    project_id: str = Field(alias="projectId")
    job_id: str = Field(alias="jobId")
    seams: list[str]
    action: Literal["toggle", "replace"]
    async_mode: bool = Field(alias="async", default=True)

    model_config = {"populate_by_name": True}
