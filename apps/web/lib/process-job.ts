/** Poll async papercraft processing jobs until complete or failed. */

import type { CraftabilityScore, ProcessStats, ProjectStatus } from "@/types";

import { abortableDelay, throwIfAborted } from "@/lib/poll-utils";

export type ProcessJobResponse = {
  jobId: string;
  projectId: string;
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  message: string;
  error?: string;
  async: boolean;
  processedModelUrl?: string;
  unfoldSvgUrl?: string;
  unfoldPdfUrl?: string;
  unfoldZipUrl?: string;
  resultStatus?: ProjectStatus;
  stats?: ProcessStats;
  craftability?: CraftabilityScore;
  exportBlocked?: boolean;
  hasUnfoldOverlap?: boolean;
};

export type PollOptions = {
  intervalMs?: number;
  timeoutMs?: number;
  signal?: AbortSignal;
  onProgress?: (job: ProcessJobResponse) => void;
};

const DEFAULT_INTERVAL_MS = 1500;
const DEFAULT_TIMEOUT_MS = 900_000;

export async function pollProcessJob(
  jobId: string,
  options: PollOptions = {},
): Promise<ProcessJobResponse> {
  const intervalMs = options.intervalMs ?? DEFAULT_INTERVAL_MS;
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const { signal } = options;
  const started = Date.now();

  while (Date.now() - started < timeoutMs) {
    throwIfAborted(signal);

    const response = await fetch(`/api/process-jobs/${jobId}`, { signal });
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as { detail?: string };
      throw new Error(body.detail ?? "Failed to fetch process job status.");
    }

    const job = (await response.json()) as ProcessJobResponse;
    throwIfAborted(signal);
    options.onProgress?.(job);

    if (job.status === "completed") {
      return job;
    }
    if (job.status === "failed") {
      throw new Error(job.error ?? "Papercraft processing failed.");
    }

    await abortableDelay(intervalMs, signal);
  }

  throw new Error("Processing timed out. Please try again later.");
}
