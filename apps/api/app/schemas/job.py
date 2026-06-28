"""Shared async job status for AI generation and papercraft processing."""

from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobKind(str, Enum):
    AI_GENERATION = "ai_generation"
    PAPERCRAFT_PROCESS = "papercraft_process"
