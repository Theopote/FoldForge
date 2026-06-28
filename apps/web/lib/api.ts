/** API response shapes for upload / project endpoints. */

import type { GenerationJobResponse } from "@/lib/generation-job";
import type { ProcessJobResponse } from "@/lib/process-job";
import { pollProcessJob } from "@/lib/process-job";
import type {
  CraftabilityScore,
  ProcessStats,
  ProjectSettings,
  ProjectStatus,
  SourceType,
} from "@/types";

export type UploadModelResponse = {
  projectId: string;
  sourceFileUrl: string;
  status: string;
};

export type ProcessModelResponse = {
  projectId: string;
  status: ProjectStatus | string;
  jobId?: string;
  async?: boolean;
  progress?: number;
  message?: string;
  processedModelUrl?: string;
  unfoldSvgUrl?: string;
  unfoldPdfUrl?: string;
  unfoldZipUrl?: string;
  stats?: ProcessStats;
  craftability?: CraftabilityScore;
};

export type GenerateModelResponse = {
  projectId: string;
  sourceType: string;
  sourceFileUrl?: string;
  sourcePrompt?: string;
  sourceImageUrl?: string;
  aiProvider: string;
  enhancedPrompt?: string;
  status: string;
  jobId?: string;
  async?: boolean;
  jobStatus?: string;
  progress?: number;
  message?: string;
};

export type ApiErrorBody = {
  detail?: string | Array<{ msg?: string; type?: string }>;
};

export type ProjectDetailResponse = {
  id: string;
  name: string;
  sourceType: SourceType;
  sourceFileUrl?: string | null;
  processedModelUrl?: string | null;
  unfoldSvgUrl?: string | null;
  unfoldPdfUrl?: string | null;
  unfoldZipUrl?: string | null;
  sourcePrompt?: string | null;
  sourceImageUrl?: string | null;
  aiProvider?: string | null;
  enhancedPrompt?: string | null;
  status: ProjectStatus;
  settings: ProjectSettings;
  stats?: ProcessStats | null;
  craftability?: CraftabilityScore | null;
  createdAt: string;
  updatedAt: string;
};

export class ProjectNotFoundError extends Error {
  constructor(projectId: string) {
    super(`Project not found: ${projectId}`);
    this.name = "ProjectNotFoundError";
  }
}

export class GenerationJobNotFoundError extends Error {
  constructor(projectId: string) {
    super(`No generation job for project: ${projectId}`);
    this.name = "GenerationJobNotFoundError";
  }
}

export class ProcessJobNotFoundError extends Error {
  constructor(projectId: string) {
    super(`No process job for project: ${projectId}`);
    this.name = "ProcessJobNotFoundError";
  }
}

/**
 * Parse FastAPI error responses into a user-facing message.
 */
export function parseApiError(body: ApiErrorBody, fallback = "Request failed."): string {
  const { detail } = body;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((item) => item.msg ?? "Validation error").join("; ");
  }
  return fallback;
}

/**
 * Fetch project metadata from the backend (source of truth).
 */
export async function getProject(projectId: string): Promise<ProjectDetailResponse> {
  const response = await fetch(`/api/projects/${projectId}`);

  if (response.status === 404) {
    throw new ProjectNotFoundError(projectId);
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new Error(parseApiError(body, "Failed to load project."));
  }

  return response.json() as Promise<ProjectDetailResponse>;
}

/**
 * Fetch the latest AI generation job for a project (resume without localStorage jobId).
 */
export async function getProjectGenerationJob(
  projectId: string,
): Promise<GenerationJobResponse> {
  const response = await fetch(`/api/projects/${projectId}/generation-job`);

  if (response.status === 404) {
    throw new GenerationJobNotFoundError(projectId);
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new Error(parseApiError(body, "Failed to load generation job."));
  }

  return response.json() as Promise<GenerationJobResponse>;
}

/**
 * Fetch the latest papercraft process job for a project (resume after reload).
 */
export async function getProjectProcessJob(
  projectId: string,
): Promise<ProcessJobResponse> {
  const response = await fetch(`/api/projects/${projectId}/process-job`);

  if (response.status === 404) {
    throw new ProcessJobNotFoundError(projectId);
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new Error(parseApiError(body, "Failed to load process job."));
  }

  return response.json() as Promise<ProcessJobResponse>;
}

/**
 * Upload a 3D model file to the backend.
 */
export async function uploadModel(file: File): Promise<UploadModelResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/api/upload-model", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new Error(parseApiError(body, "Upload failed."));
  }

  return response.json() as Promise<UploadModelResponse>;
}

/**
 * Queue papercraft processing and return the async job handle (202 Accepted).
 */
export async function startProcessModel(
  projectId: string,
  settings: Record<string, unknown>,
  options?: { signal?: AbortSignal },
): Promise<ProcessJobResponse> {
  const response = await fetch("/api/process-model", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ projectId, settings }),
    signal: options?.signal,
  });

  const body = (await response.json().catch(() => ({}))) as ProcessJobResponse &
    ApiErrorBody;

  if (response.status !== 202 && !response.ok) {
    throw new Error(parseApiError(body, "Processing failed."));
  }

  return body;
}

/** Cancel a queued or running papercraft process job. */
export async function cancelProcessJob(jobId: string): Promise<ProcessJobResponse> {
  const response = await fetch(`/api/process-jobs/${jobId}/cancel`, {
    method: "POST",
  });
  const body = (await response.json().catch(() => ({}))) as ProcessJobResponse &
    ApiErrorBody;

  if (!response.ok) {
    throw new Error(parseApiError(body, "Failed to cancel process job."));
  }

  return body;
}

/**
 * Run the papercraft generation pipeline for a project (async queue + poll).
 */
export async function processModel(
  projectId: string,
  settings: Record<string, unknown>,
  options?: {
    onProgress?: (job: ProcessJobResponse) => void;
    signal?: AbortSignal;
  },
): Promise<ProcessModelResponse> {
  const accepted = await startProcessModel(projectId, settings, {
    signal: options?.signal,
  });
  const job = await pollProcessJob(accepted.jobId, {
    onProgress: options?.onProgress,
    signal: options?.signal,
  });

  return {
    projectId: job.projectId,
    status: job.resultStatus ?? "ready",
    processedModelUrl: job.processedModelUrl,
    unfoldSvgUrl: job.unfoldSvgUrl,
    unfoldPdfUrl: job.unfoldPdfUrl,
    unfoldZipUrl: job.unfoldZipUrl,
    stats: job.stats,
    craftability: job.craftability,
    jobId: job.jobId,
    async: true,
    progress: job.progress,
    message: job.message,
  };
}

/**
 * Generate a 3D model from a text prompt (Phase 2).
 * Production providers may return 202 + jobId for async polling.
 */
export async function generateFromText(payload: {
  prompt: string;
  style: string;
  name?: string;
}): Promise<GenerateModelResponse> {
  const response = await fetch("/api/generate-from-text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const body = (await response.json().catch(() => ({}))) as GenerateModelResponse & ApiErrorBody;

  if (!response.ok) {
    throw new Error(parseApiError(body, "Text generation failed."));
  }

  return body;
}

/**
 * Generate a 3D model from a reference image (Phase 2).
 * Production providers may return 202 + jobId for async polling.
 */
export async function generateFromImage(payload: {
  file: File;
  style: string;
  hint?: string;
  name?: string;
}): Promise<GenerateModelResponse> {
  const formData = new FormData();
  formData.append("file", payload.file);
  formData.append("style", payload.style);
  if (payload.hint) formData.append("hint", payload.hint);
  if (payload.name) formData.append("name", payload.name);

  const response = await fetch("/api/generate-from-image", {
    method: "POST",
    body: formData,
  });

  const body = (await response.json().catch(() => ({}))) as GenerateModelResponse & ApiErrorBody;

  if (!response.ok) {
    throw new Error(parseApiError(body, "Image generation failed."));
  }

  return body;
}
