import { pollGenerationJob } from "@/lib/generation-job";
import { useStudioStore } from "@/store/studio-store";

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
