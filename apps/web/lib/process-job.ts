/** Poll async papercraft processing jobs until complete or failed. */

import type { CraftabilityScore, ProcessStats, ProjectStatus } from "@/types";

import { apiAuthHeaders } from "@/lib/api-auth";
import { streamJobEvents, withStreamOrFallback } from "@/lib/job-stream";
import { abortableDelay, throwIfAborted } from "@/lib/poll-utils";
import { ProcessJobCancelledError } from "@/lib/process-errors";

export type ProcessJobResponse = {
  jobId: string;
  projectId: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
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
  /** Force HTTP polling (skip SSE). */
  preferPoll?: boolean;
};

const DEFAULT_INTERVAL_MS = 1500;
const DEFAULT_TIMEOUT_MS = 900_000;

function processJobFailure(job: ProcessJobResponse): Error | null {
  if (job.status === "cancelled") {
    return new ProcessJobCancelledError(job.error ?? "Processing cancelled.");
  }
  if (job.status === "failed") {
    return new Error(job.error ?? "Papercraft processing failed.");
  }
  return null;
}

function streamProcessJob(
  jobId: string,
  options: PollOptions = {},
): Promise<ProcessJobResponse> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, signal, onProgress } = options;

  return streamJobEvents<ProcessJobResponse>(
    `/api/process-jobs/${jobId}/events`,
    {
      timeoutMs,
      signal,
      onMessage: onProgress,
      isTerminal: (job) => job.status === "completed",
      isFailure: processJobFailure,
    },
  );
}

async function pollProcessJobHttp(
  jobId: string,
  options: PollOptions = {},
): Promise<ProcessJobResponse> {
  const intervalMs = options.intervalMs ?? DEFAULT_INTERVAL_MS;
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const { signal } = options;
  const started = Date.now();

  while (Date.now() - started < timeoutMs) {
    throwIfAborted(signal);

    const response = await fetch(`/api/process-jobs/${jobId}`, {
      signal,
      headers: apiAuthHeaders(),
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as { detail?: string };
      throw new Error(body.detail ?? "Failed to fetch process job status.");
    }

    const job = (await response.json()) as ProcessJobResponse;
    throwIfAborted(signal);
    options.onProgress?.(job);

    const failure = processJobFailure(job);
    if (failure) throw failure;
    if (job.status === "completed") return job;

    await abortableDelay(intervalMs, signal);
  }

  throw new Error("Processing timed out. Please try again later.");
}

export async function pollProcessJob(
  jobId: string,
  options: PollOptions = {},
): Promise<ProcessJobResponse> {
  if (options.preferPoll) {
    return pollProcessJobHttp(jobId, options);
  }

  return withStreamOrFallback(
    () => streamProcessJob(jobId, options),
    () => pollProcessJobHttp(jobId, options),
  );
}
