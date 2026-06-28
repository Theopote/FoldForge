import {
  ProcessJobNotFoundError,
  getProjectProcessJob,
} from "@/lib/api";
import { beginJobPoll } from "@/lib/job-poll-session";
import type { ProcessJobResponse } from "@/lib/process-job";
import { pollProcessJob } from "@/lib/process-job";
import {
  clearJobProgressTracking,
  reportJobProgress,
} from "@/lib/job-progress";
import { isAbortError } from "@/lib/poll-utils";
import {
  formatProcessJobError,
  isProcessJobCancelled,
} from "@/lib/process-errors";
import { useStudioStore } from "@/store/studio-store";
import type { CraftabilityScore, ProjectStatus } from "@/types";

function applyCompletedProcessJob(job: ProcessJobResponse): void {
  const { completePapercraftProcessing, addLog } = useStudioStore.getState();

  completePapercraftProcessing({
    processedModelUrl: job.processedModelUrl ?? null,
    unfoldSvgUrl: job.unfoldSvgUrl ?? null,
    unfoldPdfUrl: job.unfoldPdfUrl ?? null,
    unfoldZipUrl: job.unfoldZipUrl ?? null,
    stats: job.stats ?? null,
    craftability: (job.craftability as CraftabilityScore | undefined) ?? null,
    status: (job.resultStatus as ProjectStatus) ?? "ready",
  });
  clearJobProgressTracking();
  addLog("Papercraft template ready.");

  if (job.stats) {
    addLog(
      `Generated ${job.stats.pieces} pieces across ${job.stats.pages} page(s), ${job.stats.faces} faces`,
    );
  }
  if (job.craftability) {
    addLog(
      `Craftability: ${job.craftability.score}/100 (${job.craftability.level})`,
    );
    for (const warning of job.craftability.warnings) {
      addLog(`Note: ${warning}`);
    }
  }
}

/** Continue polling an async papercraft process job after reload. */
export async function resumeProcessJob(jobId: string): Promise<void> {
  const { addLog, setError, setStatus, setActiveProcessJobId } =
    useStudioStore.getState();

  const signal = beginJobPoll("process");
  addLog(`Resuming papercraft processing (job ${jobId})...`);

  try {
    const job = await pollProcessJob(jobId, {
      signal,
      onProgress: (update) => {
        if (signal.aborted) return;
        setActiveProcessJobId(update.jobId);
        reportJobProgress("papercraft_process", update.progress, update.message);
      },
    });

    if (signal.aborted) return;

    applyCompletedProcessJob(job);
  } catch (error) {
    if (isAbortError(error) || isProcessJobCancelled(error)) return;

    const message = formatProcessJobError(error, "Processing resume failed.");
    setError(message);
    setStatus("failed");
    setActiveProcessJobId(null);
    clearJobProgressTracking();
    addLog(`Error: ${message}`);
  }
}

/**
 * Resume papercraft processing after reload (project has source model, status processing).
 */
export async function resumeProcessIfNeeded(
  projectId: string,
  status: ProjectStatus,
  activeProcessJobId?: string | null,
  hasSourceModel = false,
): Promise<void> {
  if (status !== "processing" || !hasSourceModel) return;

  let jobId = activeProcessJobId ?? null;

  if (!jobId) {
    try {
      const job = await getProjectProcessJob(projectId);

      if (job.status === "completed") {
        applyCompletedProcessJob(job);
        return;
      }

      if (job.status === "failed") {
        const { setStatus, setError, setActiveProcessJobId, addLog } =
          useStudioStore.getState();
        setStatus("failed");
        setError(job.error ?? "Papercraft processing failed.");
        setActiveProcessJobId(null);
        clearJobProgressTracking();
        addLog(`Error: ${job.error ?? "Papercraft processing failed."}`);
        return;
      }

      jobId = job.jobId;
      useStudioStore.getState().setActiveProcessJobId(jobId);
      reportJobProgress("papercraft_process", job.progress, job.message);
    } catch (error) {
      if (error instanceof ProcessJobNotFoundError) return;
      return;
    }
  }

  if (jobId) {
    await resumeProcessJob(jobId);
  }
}
