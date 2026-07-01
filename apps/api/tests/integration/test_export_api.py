"""Export download API edge cases."""

from __future__ import annotations

import pytest

from app.config import settings
from app.schemas.model import ProjectStatus
from app.services.project_store import project_store

pytestmark = pytest.mark.asyncio


async def test_export_requires_ready_project(api_client) -> None:
    project = project_store.create(
        project_id="exportnotready",
        name="Not Ready",
        status=ProjectStatus.UPLOADED,
    )

    response = await api_client.get(f"/api/projects/{project.id}/export/pdf")

    assert response.status_code == 409
    assert "not ready" in response.json()["detail"].lower()


async def test_export_missing_file_returns_404(api_client) -> None:
    project = project_store.create(
        project_id="exportmissing",
        name="Missing Export",
        status=ProjectStatus.READY,
    )
    project.unfold_pdf_url = "/storage/exports/missing.pdf"
    project_store.update(project)

    response = await api_client.get(f"/api/projects/{project.id}/export/pdf")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_export_existing_file_returns_download(api_client) -> None:
    pdf_path = settings.exports_dir / "ready.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    project = project_store.create(
        project_id="exportready",
        name="Ready Export",
        status=ProjectStatus.READY,
    )
    project.unfold_pdf_url = "/storage/exports/ready.pdf"
    project_store.update(project)

    response = await api_client.get(f"/api/projects/{project.id}/export/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")


async def test_export_instructions_pdf_returns_download(api_client) -> None:
    instructions_path = settings.exports_dir / "instr-ready.instructions.pdf"
    instructions_path.write_bytes(b"%PDF-1.4\n")
    project = project_store.create(
        project_id="instr-ready",
        name="Instructions Export",
        status=ProjectStatus.READY,
    )

    response = await api_client.get(
        f"/api/projects/{project.id}/export/instructions-pdf",
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert "instructions" in response.headers.get("content-disposition", "").lower()


async def test_export_instructions_pdf_missing_returns_404(api_client) -> None:
    project = project_store.create(
        project_id="instr-missing",
        name="Missing Instructions",
        status=ProjectStatus.READY,
    )

    response = await api_client.get(
        f"/api/projects/{project.id}/export/instructions-pdf",
    )

    assert response.status_code == 404
