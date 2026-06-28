/** Poll async AI generation jobs until complete or failed. */

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
};

const DEFAULT_INTERVAL_MS = 2000;
const DEFAULT_TIMEOUT_MS = 600_000;

/**
 * Poll a generation job until it completes or fails.
 */
export async function pollGenerationJob(
  jobId: string,
  options: PollOptions = {},
): Promise<GenerationJobResponse> {
  const intervalMs = options.intervalMs ?? DEFAULT_INTERVAL_MS;
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const { signal } = options;
  const started = Date.now();

  while (Date.now() - started < timeoutMs) {
    throwIfAborted(signal);

    const response = await fetch(`/api/generation-jobs/${jobId}`, { signal });
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as { detail?: string };
      throw new Error(body.detail ?? "Failed to fetch generation job status.");
    }

    const job = (await response.json()) as GenerationJobResponse;
    throwIfAborted(signal);
    options.onProgress?.(job);

    if (job.status === "completed") {
      return job;
    }
    if (job.status === "failed") {
      throw new Error(job.error ?? "AI generation failed.");
    }

    await abortableDelay(intervalMs, signal);
  }

  throw new Error("Generation timed out. Please try again later.");
}
