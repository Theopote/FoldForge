import { useStudioStore } from "@/store/studio-store";

export type JobPhase = "idle" | "ai_generation" | "papercraft_process";

let lastLoggedMessage = "";

/** Update global job progress and append new backend messages to the processing log. */
export function reportJobProgress(
  phase: JobPhase,
  progress: number,
  message: string,
): void {
  const store = useStudioStore.getState();
  store.setJobProgress({ phase, progress, message });

  const trimmed = message.trim();
  if (trimmed && trimmed !== lastLoggedMessage) {
    lastLoggedMessage = trimmed;
    store.addLog(trimmed);
  }
}

/** Reset transient job progress UI (call when a job finishes or is cancelled). */
export function clearJobProgressTracking(): void {
  lastLoggedMessage = "";
  useStudioStore.getState().clearJobProgress();
}
