import {
  GenerationJobNotFoundError,
  getProjectGenerationJob,
} from "@/lib/api";
import type { GenerationJobResponse } from "@/lib/generation-job";
import { pollGenerationJob } from "@/lib/generation-job";
import { useStudioStore } from "@/store/studio-store";
import type { ProjectStatus } from "@/types";

function applyCompletedGenerationJob(job: GenerationJobResponse): void {
  const {
    projectId,
    projectName,
    sourceType,
    sourcePrompt,
    sourceImageUrl,
    setGenerationResult,
    addLog,
  } = useStudioStore.getState();

  if (!projectId || !job.sourceFileUrl) return;

  setGenerationResult({
    projectId,
    sourceFileUrl: job.sourceFileUrl,
    fileName: `${projectName}.glb`,
    sourceType,
    sourcePrompt,
    sourceImageUrl: job.sourceImageUrl ?? sourceImageUrl,
    aiProvider: job.provider,
    enhancedPrompt: job.enhancedPrompt,
  });
  addLog(`AI model ready (${job.provider}). Project: ${projectId}`);
}

/** Continue polling an async AI job after the page reloads. */
export async function resumeGenerationJob(jobId: string): Promise<void> {
  const store = useStudioStore.getState();
  const {
    projectId,
    projectName,
    sourceType,
    sourcePrompt,
    sourceImageUrl,
    setGenerationResult,
    setStatus,
    setActiveJobId,
    addLog,
    setError,
  } = store;

  if (!projectId) return;

  addLog(`Resuming AI generation (job ${jobId})...`);

  try {
    const job = await pollGenerationJob(jobId);

    if (!job.sourceFileUrl) {
      throw new Error("Generation completed but no model URL was returned.");
    }

    setGenerationResult({
      projectId,
      sourceFileUrl: job.sourceFileUrl,
      fileName: `${projectName}.glb`,
      sourceType,
      sourcePrompt,
      sourceImageUrl: job.sourceImageUrl ?? sourceImageUrl,
      aiProvider: job.provider,
      enhancedPrompt: job.enhancedPrompt,
    });
    addLog(`AI model ready (${job.provider}). Project: ${projectId}`);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Generation resume failed.";
    setError(message);
    setStatus("failed");
    setActiveJobId(null);
    addLog(`Error: ${message}`);
  }
}

/**
 * Resume AI generation after reload when localStorage may lack jobId.
 * Skips papercraft pipeline runs (processing with an existing source model).
 */
export async function resumeGenerationIfNeeded(
  projectId: string,
  status: ProjectStatus,
  activeJobId?: string | null,
  hasSourceModel = false,
): Promise<void> {
  if (status !== "processing" || hasSourceModel) return;

  let jobId = activeJobId ?? null;

  if (!jobId) {
    try {
      const job = await getProjectGenerationJob(projectId);

      if (job.status === "completed") {
        applyCompletedGenerationJob(job);
        return;
      }

      if (job.status === "failed") {
        const { setStatus, setError, setActiveJobId, addLog } =
          useStudioStore.getState();
        setStatus("failed");
        setError(job.error ?? "AI generation failed.");
        setActiveJobId(null);
        addLog(`Error: ${job.error ?? "AI generation failed."}`);
        return;
      }

      jobId = job.jobId;
      useStudioStore.getState().setActiveJobId(jobId);
    } catch (error) {
      if (error instanceof GenerationJobNotFoundError) return;
      // Network or server error — cannot resolve jobId without the backend.
      return;
    }
  }

  if (jobId) {
    await resumeGenerationJob(jobId);
  }
}
