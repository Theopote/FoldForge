import { patchProjectSettings } from "@/lib/api";
import type { ProjectSettings } from "@/types";

const DEBOUNCE_MS = 400;

let hydratePaused = false;
let pendingProjectId: string | null = null;
let pendingSettings: ProjectSettings | null = null;
let debounceTimer: ReturnType<typeof setTimeout> | null = null;
let flushing = false;

/** Skip PATCH while hydrating from the backend (avoid echo writes). */
export function pauseProjectSettingsSync(): void {
  hydratePaused = true;
}

export function resumeProjectSettingsSync(): void {
  hydratePaused = false;
}

export function scheduleProjectSettingsSync(
  projectId: string,
  settings: ProjectSettings,
): void {
  if (hydratePaused || typeof window === "undefined") return;

  pendingProjectId = projectId;
  pendingSettings = settings;

  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    debounceTimer = null;
    void flushProjectSettingsSync();
  }, DEBOUNCE_MS);
}

async function flushProjectSettingsSync(): Promise<void> {
  if (flushing || !pendingProjectId || !pendingSettings) return;

  const projectId = pendingProjectId;
  const settings = pendingSettings;
  pendingSettings = null;
  flushing = true;

  try {
    await patchProjectSettings(projectId, settings);
  } catch {
    // Settings stay in memory; next edit or process-model will retry persistence.
  } finally {
    flushing = false;
    if (pendingSettings && pendingProjectId) {
      void flushProjectSettingsSync();
    }
  }
}
