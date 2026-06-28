"""Bad mesh handling tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.pipeline_errors import UnfoldRepairError
from tests.conftest import wait_for_process_job


def test_unfold_repair_error_carries_warnings() -> None:
    error = UnfoldRepairError("Unfold overlaps remain.", warnings=["overlap detected"])
    assert error.warnings == ["overlap detected"]


@pytest.mark.asyncio
async def test_bad_mesh_process_job_returns_clear_failure(
    api_client,
    fixtures_dir: Path,
) -> None:
    """Non-manifold uploads should fail or complete with explicit warnings."""
    fixture = fixtures_dir / "non_manifold_bad_mesh.stl"
    assert fixture.exists()

    with fixture.open("rb") as handle:
        upload = await api_client.post(
            "/api/upload-model",
            files={"file": ("non_manifold_bad_mesh.stl", handle, "model/stl")},
        )
    assert upload.status_code == 200
    project_id = upload.json()["projectId"]

    process = await api_client.post(
        "/api/process-model",
        json={
            "projectId": project_id,
            "settings": {
                "paperSize": "A4",
                "difficulty": "standard",
                "style": "low_poly",
                "targetHeightMm": 80,
                "addTabs": False,
                "addNumbers": True,
                "addFoldLines": True,
                "addCutLines": True,
            },
        },
    )
    assert process.status_code == 202
    job_id = process.json()["jobId"]

    job = await wait_for_process_job(api_client, job_id, timeout_sec=240.0)
    if job["status"] == "completed":
        warnings = job.get("craftability", {}).get("warnings") or []
        assert warnings, "Expected craftability warnings for bad mesh"
        return

    assert job["status"] == "failed"
    error_text = (job.get("error") or job.get("message") or "").lower()
    assert error_text
