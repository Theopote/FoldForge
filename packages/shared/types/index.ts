export type SourceType = "upload_3d" | "text_to_3d" | "image_to_3d";

export type ProjectStatus =
  | "created"
  | "uploaded"
  | "processing"
  | "ready"
  | "failed";

export type PaperSize = "A4" | "A3" | "Letter";
export type Difficulty = "easy" | "standard" | "advanced";
export type Style = "low_poly" | "cute" | "geometric";
export type ColorMode = "color" | "line_art";

export type ProjectSettings = {
  paperSize: PaperSize;
  difficulty: Difficulty;
  style: Style;
  targetHeightMm: number;
  addTabs: boolean;
  addNumbers: boolean;
  addFoldLines: boolean;
  addCutLines: boolean;
  colorMode: ColorMode;
};

export type Project = {
  id: string;
  name: string;
  sourceType: SourceType;
  sourceFileUrl?: string;
  processedModelUrl?: string;
  unfoldSvgUrl?: string;
  unfoldPdfUrl?: string;
  unfoldZipUrl?: string;
  status: ProjectStatus;
  settings: ProjectSettings;
  createdAt: string;
  updatedAt: string;
};

export type Point2D = { x: number; y: number };

export type Tab = {
  id: string;
  edgeId: string;
  polygon: Point2D[];
  targetPieceId: string;
  label: string;
};

export type FoldLine = {
  id: string;
  from: Point2D;
  to: Point2D;
  type: "mountain" | "valley";
};

export type CutLine = {
  id: string;
  from: Point2D;
  to: Point2D;
};

export type UnfoldPiece = {
  id: string;
  faceIds: number[];
  polygon: Point2D[];
  tabs: Tab[];
  foldLines: FoldLine[];
  cutLines: CutLine[];
  label: string;
};

export type CraftabilityLevel = "excellent" | "good" | "fair" | "poor";

export type CraftabilityScore = {
  score: number;
  level: CraftabilityLevel;
  warnings: string[];
};

export type ProcessStats = {
  faces: number;
  pieces: number;
  pages: number;
  difficultyScore: number;
};

export const DEFAULT_PROJECT_SETTINGS: ProjectSettings = {
  paperSize: "A4",
  difficulty: "standard",
  style: "low_poly",
  targetHeightMm: 200,
  addTabs: true,
  addNumbers: true,
  addFoldLines: true,
  addCutLines: true,
  colorMode: "line_art",
};
