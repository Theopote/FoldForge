/** Poll async papercraft processing jobs until complete or failed. */

import type { CraftabilityScore, ProcessStats, ProjectStatus } from "@/types";

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
};

export type PollOptions = {
  intervalMs?: number;
  timeoutMs?: number;
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
  const started = Date.now();

  while (Date.now() - started < timeoutMs) {
    const response = await fetch(`/api/process-jobs/${jobId}`);
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as { detail?: string };
      throw new Error(body.detail ?? "Failed to fetch process job status.");
    }

    const job = (await response.json()) as ProcessJobResponse;
    options.onProgress?.(job);

    if (job.status === "completed") {
      return job;
    }
    if (job.status === "failed") {
      throw new Error(job.error ?? "Papercraft processing failed.");
    }

    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }

  throw new Error("Processing timed out. Please try again later.");
}
