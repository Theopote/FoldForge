"""Process job API surfaces layout-fit failures without partial export."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import wait_for_process_job


@pytest.mark.asyncio
async def test_process_job_fails_when_layout_cannot_place_all_pieces(
    api_client,
    test_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    fixtures_dir: Path,
) -> None:
    from app.services.layout_repair import LayoutRepairResult

    def blocked_layout(*_args, **_kwargs) -> LayoutRepairResult:
        return LayoutRepairResult(
            pages=[],
            messages=[
                "Could not place piece(s) Ghost on the page — layout export blocked."
            ],
            export_blocked=True,
            suggestions=[
                "Use a larger paper size (e.g. A3 instead of A4).",
                "Switch to Easy mode to split the model into smaller patches.",
            ],
        )

    monkeypatch.setattr(
        "app.services.papercraft_pipeline.layout_with_repair",
        blocked_layout,
    )

    fixture = fixtures_dir / "cube.stl"
    if not fixture.exists():
        pytest.skip("Missing cube.stl fixture")

    with fixture.open("rb") as handle:
        upload = await api_client.post(
            "/api/upload-model",
            files={"file": ("cube.stl", handle, "model/stl")},
        )
    assert upload.status_code == 200
    project_id = upload.json()["projectId"]

    process = await api_client.post(
        "/api/process-model",
        json={
            "projectId": project_id,
            "settings": {
                "paperSize": "A4",
                "difficulty": "easy",
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

    job = await wait_for_process_job(api_client, job_id, timeout_sec=120.0)

    assert job["status"] == "failed"
    assert job["resultStatus"] == "failed"
    assert "Ghost" in (job.get("error") or "")
    assert job.get("unfoldPdfUrl") in (None, "")
    assert job.get("unfoldSvgUrl") in (None, "")

    project = await api_client.get(f"/api/projects/{project_id}")
    assert project.status_code == 200
    assert project.json()["status"] == "failed"
