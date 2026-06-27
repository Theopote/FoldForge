import type {
  CraftabilityScore,
  ProcessStats,
  ProjectSettings,
  ProjectStatus,
} from "@/types";

const STORAGE_KEY = "foldforge:last-project";

export type SavedStudioProject = {
  projectId: string;
  projectName: string;
  sourceFileName: string | null;
  sourceFileUrl: string | null;
  processedModelUrl: string | null;
  unfoldSvgUrl: string | null;
  unfoldPdfUrl: string | null;
  unfoldZipUrl: string | null;
  status: ProjectStatus;
  settings: ProjectSettings;
  stats: ProcessStats | null;
  craftability: CraftabilityScore | null;
  savedAt: string;
};

export function saveStudioProject(data: Omit<SavedStudioProject, "savedAt">): void {
  if (typeof window === "undefined") return;

  const payload: SavedStudioProject = {
    ...data,
    savedAt: new Date().toISOString(),
  };

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Quota exceeded or private mode — ignore silently for MVP
  }
}

export function loadStudioProject(): SavedStudioProject | null {
  if (typeof window === "undefined") return null;

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as SavedStudioProject;
  } catch {
    return null;
  }
}

export function clearStudioProject(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}
