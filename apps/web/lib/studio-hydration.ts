import { resumeGenerationIfNeeded } from "@/features/studio/resume-generation";
import { resumeProcessIfNeeded } from "@/features/studio/resume-process";
import { ProjectNotFoundError, getProject } from "@/lib/api";
import {
  persistLastProjectId,
  projectDetailToStudioSnapshot,
} from "@/lib/project-storage";
import { useStudioStore } from "@/store/studio-store";

export type StudioHydrationResult = "ok" | "not_found" | "offline";

/**
 * Load project state from the backend and resume in-flight jobs.
 * Backend SQLite is the source of truth; job ids come from generation/process job APIs.
 */
export async function hydrateStudioProject(
  projectId: string,
): Promise<StudioHydrationResult> {
  try {
    const remote = await getProject(projectId);
    const snapshot = projectDetailToStudioSnapshot(remote);

    useStudioStore.getState().restoreProject(snapshot);
    persistLastProjectId(projectId);

    const hasSource = Boolean(snapshot.sourceFileUrl);
    await resumeGenerationIfNeeded(
      snapshot.projectId,
      snapshot.status,
      null,
      hasSource,
    );
    await resumeProcessIfNeeded(
      snapshot.projectId,
      snapshot.status,
      null,
      hasSource,
    );

    return "ok";
  } catch (error) {
    if (error instanceof ProjectNotFoundError) {
      return "not_found";
    }
    return "offline";
  }
}
