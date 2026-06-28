import type { ProjectDetailResponse } from "@/lib/api";
import type {
  CraftabilityScore,
  ProcessStats,
  ProjectSettings,
  ProjectStatus,
  SourceType,
} from "@/types";

const STORAGE_KEY = "foldforge:last-project";

export { STORAGE_KEY as STUDIO_SESSION_STORAGE_KEY };

/**
 * Studio session pointer — only the project id is cached locally.
 * Project metadata and job state come from the backend (SQLite).
 */

export type StudioProjectSnapshot = {
  projectId: string;
  projectName: string;
  sourceType: SourceType;
  sourceFileName: string | null;
  sourceFileUrl: string | null;
  sourcePrompt?: string | null;
  sourceImageUrl?: string | null;
  aiProvider?: string | null;
  enhancedPrompt?: string | null;
  activeJobId?: string | null;
  activeProcessJobId?: string | null;
  processedModelUrl: string | null;
  unfoldSvgUrl: string | null;
  unfoldPdfUrl: string | null;
  unfoldZipUrl: string | null;
  status: ProjectStatus;
  settings: ProjectSettings;
  stats: ProcessStats | null;
  craftability: CraftabilityScore | null;
};

type LastStudioSession = {
  projectId: string;
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

/** Map backend project payload into studio store shape. */
export function projectDetailToStudioSnapshot(
  project: ProjectDetailResponse,
): StudioProjectSnapshot {
  return {
    projectId: project.id,
    projectName: project.name,
    sourceType: project.sourceType,
    sourceFileName: fileNameFromUrl(project.sourceFileUrl ?? null),
    sourceFileUrl: project.sourceFileUrl ?? null,
    sourcePrompt: project.sourcePrompt ?? null,
    sourceImageUrl: project.sourceImageUrl ?? null,
    aiProvider: project.aiProvider ?? null,
    enhancedPrompt: project.enhancedPrompt ?? null,
    activeJobId: null,
    activeProcessJobId: null,
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

/** Remember which project the user last opened in Studio. */
export function persistLastProjectId(projectId: string): void {
  if (typeof window === "undefined" || !projectId) return;

  const payload: LastStudioSession = {
    projectId,
    savedAt: new Date().toISOString(),
  };

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Quota exceeded or private mode — ignore silently
  }
}

/** Read the last studio project id (supports legacy full-state cache). */
export function loadLastProjectId(): string | null {
  if (typeof window === "undefined") return null;

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw) as { projectId?: unknown };
    return typeof parsed.projectId === "string" && parsed.projectId
      ? parsed.projectId
      : null;
  } catch {
    return null;
  }
}

export function clearLastProjectId(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}

export function resolveStudioProjectId(
  urlProjectId: string | null,
  storedProjectId: string | null,
): string | null {
  if (urlProjectId) return urlProjectId;
  return storedProjectId;
}
