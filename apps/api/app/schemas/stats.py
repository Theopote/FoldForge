"""Shared processing result schemas."""

from pydantic import BaseModel, Field


class ProcessStats(BaseModel):
    faces: int = 0
    pieces: int = 0
    pages: int = 0
    difficulty_score: int = Field(alias="difficultyScore", default=0)

    model_config = {"populate_by_name": True}


class CraftabilityScore(BaseModel):
    score: int
    level: str
    warnings: list[str] = Field(default_factory=list)
