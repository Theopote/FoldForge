"""Helpers for pipeline snapshot and export assertions."""

from __future__ import annotations

import json
import os
from pathlib import Path

from app.models.geometry import PipelineResult


def summarize_pipeline(
    result: PipelineResult,
    *,
    svg_path: Path,
    pdf_path: Path,
) -> dict:
    fold_lines = sum(len(piece.fold_lines) for piece in result.pieces)
    cut_lines = sum(len(piece.cut_lines) for piece in result.pieces)
    tabs = sum(len(piece.tabs) for piece in result.pieces)
    return {
        "pieces": len(result.pieces),
        "pages": len(result.pages),
        "face_count": result.face_count,
        "fold_lines": fold_lines,
        "cut_lines": cut_lines,
        "tabs": tabs,
        "piece_overlaps": sum(1 for piece in result.pieces if piece.has_overlap),
        "scaled_piece_count": sum(
            1
            for page in result.pages
            for placed in page.placed_pieces
            if placed.piece.id.endswith("-scaled")
        ),
        "craftability_score": result.craftability_score,
        "craftability_level": result.craftability_level,
        "warning_count": len(result.warnings),
        "svg_bytes": svg_path.stat().st_size if svg_path.exists() else 0,
        "pdf_bytes": pdf_path.stat().st_size if pdf_path.exists() else 0,
    }


def assert_pipeline_snapshot(fixture_stem: str, metrics: dict) -> None:
    snapshot_dir = Path(__file__).resolve().parent.parent / "snapshots" / "pipeline"
    snapshot_path = snapshot_dir / f"{fixture_stem}.json"

    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return

    if not snapshot_path.exists():
        raise AssertionError(
            f"Missing snapshot {snapshot_path.name}. "
            f"Run UPDATE_SNAPSHOTS=1 pytest to create it."
        )

    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert metrics == expected, (
        f"Pipeline snapshot mismatch for {fixture_stem}. "
        f"Set UPDATE_SNAPSHOTS=1 to refresh if intentional."
    )


def assert_svg_export(path: Path, *, project_name: str) -> None:
    assert path.exists(), f"SVG not written: {path}"
    content = path.read_text(encoding="utf-8")
    assert content.startswith("<?xml") or "<svg" in content[:200]
    assert "viewBox=" in content
    assert project_name in content
    assert "stroke" in content
    assert "Scale check" in content
    assert "Legend" in content
    assert path.stat().st_size > 500


def assert_pdf_export(path: Path) -> None:
    assert path.exists(), f"PDF not written: {path}"
    header = path.read_bytes()[:8]
    assert header.startswith(b"%PDF"), f"Invalid PDF header: {header!r}"
    assert path.stat().st_size > 400
