"""Internal geometry datatypes for the papercraft pipeline."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Point2D:
    x: float
    y: float

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass
class Tab:
    id: str
    edge_id: str
    polygon: list[Point2D]
    target_piece_id: str
    label: str


@dataclass
class FoldLine:
    id: str
    start: Point2D
    end: Point2D
    fold_type: Literal["mountain", "valley"]


@dataclass
class CutLine:
    id: str
    start: Point2D
    end: Point2D
    mesh_edge: tuple[int, int] | None = None


@dataclass
class BakedTriangle:
    """Filled unfold triangle sampled from the source mesh surface."""

    a: Point2D
    b: Point2D
    c: Point2D
    fill: str


@dataclass
class UnfoldPiece:
    id: str
    face_ids: list[int]
    polygon: list[Point2D]
    tabs: list[Tab] = field(default_factory=list)
    fold_lines: list[FoldLine] = field(default_factory=list)
    cut_lines: list[CutLine] = field(default_factory=list)
    label: str = ""
    has_overlap: bool = False
    cut_outline: list[Point2D] | None = None
    baked_triangles: list[BakedTriangle] = field(default_factory=list)


@dataclass
class PlacedPiece:
    """A piece positioned on a paper page (coordinates in mm)."""

    piece: UnfoldPiece
    offset_x: float
    offset_y: float
    page_index: int


@dataclass
class LayoutPage:
    index: int
    width_mm: float
    height_mm: float
    placed_pieces: list[PlacedPiece]


@dataclass
class PipelineResult:
    processed_mesh_path: str
    svg_path: str
    pdf_path: str
    zip_path: str
    pieces: list[UnfoldPiece]
    pages: list[LayoutPage]
    face_count: int
    difficulty_score: int
    craftability_score: int
    craftability_level: str
    warnings: list[str]
    export_blocked: bool = False
    has_unfold_overlap: bool = False
