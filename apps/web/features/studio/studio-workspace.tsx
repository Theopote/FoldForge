"use client";

import { useEffect } from "react";

import { CraftabilityCard } from "@/features/craftability/craftability-card";
import { ProcessingLogPanel } from "@/features/export-panel/processing-log-panel";
import { ModelPreviewPanel } from "@/features/model-preview/model-preview-panel";
import { CreateSourcePanel } from "@/features/model-upload/create-source-panel";
import { ProjectSettingsPanel } from "@/features/project-settings/project-settings-panel";
import { UnfoldPreviewPanel } from "@/features/unfold-preview/unfold-preview-panel";
import { ProjectNotFoundError, getProject } from "@/lib/api";
import {
  clearStudioProject,
  loadStudioProject,
  projectDetailToSavedStudio,
  saveStudioProject,
} from "@/lib/project-storage";
import { useStudioStore } from "@/store/studio-store";

export function StudioWorkspace() {
  const { projectId, status, craftability, restoreProject, addLog } =
    useStudioStore();

  useEffect(() => {
    if (projectId) return;

    const saved = loadStudioProject();
    if (!saved?.projectId) return;

    let cancelled = false;

    void (async () => {
      try {
        const remote = await getProject(saved.projectId);
        if (cancelled) return;

        const payload = projectDetailToSavedStudio(remote, {
          sourceFileName: saved.sourceFileName,
        });
        restoreProject({ ...payload, savedAt: saved.savedAt });
        saveStudioProject(payload);
        addLog(`Restored project: ${remote.name}`);
      } catch (error) {
        if (cancelled) return;

        if (error instanceof ProjectNotFoundError) {
          clearStudioProject();
          addLog("Previous project no longer exists — starting fresh.");
          return;
        }

        restoreProject(saved);
        addLog(
          `Restored from local cache (${saved.projectName}); server unavailable.`,
        );
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [projectId, restoreProject, addLog]);

  return (
    <>
      <div className="grid gap-6 lg:grid-cols-12">
        <aside className="space-y-6 lg:col-span-3">
          <section className="rounded-2xl border border-border/70 bg-card p-4">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Create
            </h2>
            <CreateSourcePanel />
          </section>
          <ProjectSettingsPanel />
          {status === "ready" && (
            <CraftabilityCard craftability={craftability} />
          )}
        </aside>

        <section className="lg:col-span-5">
          <ModelPreviewPanel />
        </section>

        <section className="lg:col-span-4">
          <UnfoldPreviewPanel />
        </section>
      </div>

      <div className="mt-6">
        <ProcessingLogPanel />
      </div>
    </>
  );
}
