"""Plan ordered assembly steps from unfold geometry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.models.geometry import Tab, UnfoldPiece
from app.schemas.model import ProjectSettings


StepKind = Literal["overview", "prepare", "join"]


@dataclass(frozen=True)
class AssemblyStep:
    number: int
    kind: StepKind
    title: str
    detail: str
    primary_piece_id: str
    secondary_piece_id: str | None = None
    tab: Tab | None = None
    tab_owner_piece_id: str | None = None
    assembled_piece_ids: tuple[str, ...] = ()


def plan_assembly_steps(
    pieces: list[UnfoldPiece],
    settings: ProjectSettings,
) -> list[AssemblyStep]:
    """Build a printable step sequence from piece size and tab pairings."""
    if not pieces:
        return []

    ordered = sorted(
        pieces,
        key=lambda piece: (-len(piece.face_ids), -len(piece.polygon), piece.label),
    )
    piece_by_id = {piece.id: piece for piece in ordered}

    if not settings.add_tabs:
        return [
            AssemblyStep(
                number=1,
                kind="overview",
                title="Prepare all pieces",
                detail=f"Cut and score {len(ordered)} pieces.",
                primary_piece_id=ordered[0].id,
                assembled_piece_ids=tuple(piece.id for piece in ordered),
            ),
            *[
                AssemblyStep(
                    number=index + 2,
                    kind="prepare",
                    title=f"Assemble piece {piece.label}",
                    detail="Glue shared edges to previously assembled parts.",
                    primary_piece_id=piece.id,
                    assembled_piece_ids=tuple(ordered[i].id for i in range(index)),
                )
                for index, piece in enumerate(ordered)
            ],
        ]

    steps: list[AssemblyStep] = [
        AssemblyStep(
            number=1,
            kind="overview",
            title="Prepare all pieces",
            detail=f"Cut, score, and lay out {len(ordered)} labeled pieces before gluing.",
            primary_piece_id=ordered[0].id,
            assembled_piece_ids=tuple(piece.id for piece in ordered),
        )
    ]

    assembled: set[str] = set()
    step_number = 2

    for index, piece in enumerate(ordered):
        if index == 0:
            steps.append(
                AssemblyStep(
                    number=step_number,
                    kind="prepare",
                    title=f"Pre-fold piece {piece.label}",
                    detail="Score all fold lines on this piece before attaching tabs.",
                    primary_piece_id=piece.id,
                    assembled_piece_ids=tuple(assembled),
                )
            )
            step_number += 1
            assembled.add(piece.id)
            continue

        join = _find_join_connection(piece, assembled, piece_by_id)
        if join is not None:
            tab_owner, tab, target = join
            attaching = piece if tab_owner.id != piece.id else piece_by_id[piece.id]
            steps.append(
                AssemblyStep(
                    number=step_number,
                    kind="join",
                    title=f"Attach piece {attaching.label}",
                    detail=f"Apply glue to tab {tab.label or attaching.label + '-' + target.label} and join to piece {target.label}.",
                    primary_piece_id=attaching.id,
                    secondary_piece_id=target.id,
                    tab=tab,
                    tab_owner_piece_id=tab_owner.id,
                    assembled_piece_ids=tuple(assembled),
                )
            )
        else:
            steps.append(
                AssemblyStep(
                    number=step_number,
                    kind="prepare",
                    title=f"Add piece {piece.label}",
                    detail="Fold and glue this piece to the assembly using matching tabs.",
                    primary_piece_id=piece.id,
                    assembled_piece_ids=tuple(assembled),
                )
            )

        step_number += 1
        assembled.add(piece.id)

    return steps


def _find_join_connection(
    piece: UnfoldPiece,
    assembled: set[str],
    piece_by_id: dict[str, UnfoldPiece],
) -> tuple[UnfoldPiece, Tab, UnfoldPiece] | None:
    for tab in piece.tabs:
        if tab.target_piece_id in assembled:
            return piece, tab, piece_by_id[tab.target_piece_id]

    for assembled_id in assembled:
        owner = piece_by_id[assembled_id]
        for tab in owner.tabs:
            if tab.target_piece_id == piece.id:
                return owner, tab, piece

    return None


def format_assembly_step_lines(steps: list[AssemblyStep]) -> list[str]:
    return [f"Step {step.number}: {step.title} — {step.detail}" for step in steps]
