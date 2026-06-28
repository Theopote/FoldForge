import type { ProjectDetailResponse } from "@/lib/api";
import type {
  CraftabilityScore,
  ProcessStats,
  ProjectSettings,
  ProjectStatus,
  SourceType,
} from "@/types";

const STORAGE_KEY = "foldforge:last-project";

export type SavedStudioProject = {
  projectId: string;
  projectName: string;
  sourceType: SourceType;
  sourceFileName: string | null;
  sourceFileUrl: string | null;
  sourcePrompt?: string | null;
  sourceImageUrl?: string | null;
  aiProvider?: string | null;
  enhancedPrompt?: string | null;
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

function fileNameFromUrl(url: string | null | undefined): string | null {
  if (!url) return null;

  try {
    const path = new URL(url, "http://local").pathname;
    const name = path.split("/").pop();
    return name ? decodeURIComponent(name) : null;
  } catch {
    const name = url.split("/").pop();
    return name ? decodeURIComponent(name) : null;
  }
}

/** Map backend project payload into studio localStorage shape. */
export function projectDetailToSavedStudio(
  project: ProjectDetailResponse,
  fallback?: Pick<SavedStudioProject, "sourceFileName">,
): Omit<SavedStudioProject, "savedAt"> {
  return {
    projectId: project.id,
    projectName: project.name,
    sourceType: project.sourceType,
    sourceFileName:
      fallback?.sourceFileName ?? fileNameFromUrl(project.sourceFileUrl ?? null),
    sourceFileUrl: project.sourceFileUrl ?? null,
    sourcePrompt: project.sourcePrompt ?? null,
    sourceImageUrl: project.sourceImageUrl ?? null,
    aiProvider: project.aiProvider ?? null,
    enhancedPrompt: project.enhancedPrompt ?? null,
    processedModelUrl: project.processedModelUrl ?? null,
    unfoldSvgUrl: project.unfoldSvgUrl ?? null,
    unfoldPdfUrl: project.unfoldPdfUrl ?? null,
    unfoldZipUrl: project.unfoldZipUrl ?? null,
    status: project.status,
    settings: project.settings,
    stats: project.stats ?? null,
    craftability: project.craftability ?? null,
  };
}

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
