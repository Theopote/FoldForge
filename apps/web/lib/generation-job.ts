/** Poll async AI generation jobs until complete or failed. */

import { apiAuthHeaders } from "@/lib/api-auth";
import { streamJobEvents, withStreamOrFallback } from "@/lib/job-stream";
import { abortableDelay, throwIfAborted } from "@/lib/poll-utils";

export type GenerationJobResponse = {
  jobId: string;
  projectId: string;
  status: "queued" | "running" | "completed" | "failed";
  provider: string;
  progress: number;
  message: string;
  error?: string;
  async: boolean;
  sourceFileUrl?: string;
  sourceImageUrl?: string;
  enhancedPrompt?: string;
};

export type PollOptions = {
  intervalMs?: number;
  timeoutMs?: number;
  signal?: AbortSignal;
  onProgress?: (job: GenerationJobResponse) => void;
  preferPoll?: boolean;
};

const DEFAULT_INTERVAL_MS = 2000;
const DEFAULT_TIMEOUT_MS = 600_000;

function generationJobFailure(job: GenerationJobResponse): Error | null {
  if (job.status === "failed") {
    return new Error(job.error ?? "AI generation failed.");
  }
  return null;
}

function streamGenerationJob(
  jobId: string,
  options: PollOptions = {},
): Promise<GenerationJobResponse> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, signal, onProgress } = options;

  return streamJobEvents<GenerationJobResponse>(
    `/api/generation-jobs/${jobId}/events`,
    {
      timeoutMs,
      signal,
      onMessage: onProgress,
      isTerminal: (job) => job.status === "completed",
      isFailure: generationJobFailure,
    },
  );
}

async function pollGenerationJobHttp(
  jobId: string,
  options: PollOptions = {},
): Promise<GenerationJobResponse> {
  const intervalMs = options.intervalMs ?? DEFAULT_INTERVAL_MS;
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const { signal } = options;
  const started = Date.now();

  while (Date.now() - started < timeoutMs) {
    throwIfAborted(signal);

    const response = await fetch(`/api/generation-jobs/${jobId}`, {
      signal,
      headers: apiAuthHeaders(),
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as { detail?: string };
      throw new Error(body.detail ?? "Failed to fetch generation job status.");
    }

    const job = (await response.json()) as GenerationJobResponse;
    throwIfAborted(signal);
    options.onProgress?.(job);

    const failure = generationJobFailure(job);
    if (failure) throw failure;
    if (job.status === "completed") return job;

    await abortableDelay(intervalMs, signal);
  }

  throw new Error("Generation timed out. Please try again later.");
}

/**
 * Wait for a generation job via SSE, falling back to HTTP polling.
 */
export async function pollGenerationJob(
  jobId: string,
  options: PollOptions = {},
): Promise<GenerationJobResponse> {
  if (options.preferPoll) {
    return pollGenerationJobHttp(jobId, options);
  }

  return withStreamOrFallback(
    () => streamGenerationJob(jobId, options),
    () => pollGenerationJobHttp(jobId, options),
    options.signal,
  );
}
