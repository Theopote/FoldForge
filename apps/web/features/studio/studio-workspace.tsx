"use client";

import { useEffect } from "react";

import { CraftabilityCard } from "@/features/craftability/craftability-card";
import { ProcessingLogPanel } from "@/features/export-panel/processing-log-panel";
import { ModelPreviewPanel } from "@/features/model-preview/model-preview-panel";
import { ModelUploadPanel } from "@/features/model-upload/model-upload-panel";
import { ProjectSettingsPanel } from "@/features/project-settings/project-settings-panel";
import { UnfoldPreviewPanel } from "@/features/unfold-preview/unfold-preview-panel";
import { loadStudioProject } from "@/lib/project-storage";
import { useStudioStore } from "@/store/studio-store";

export function StudioWorkspace() {
  const { projectId, status, craftability, restoreProject, addLog } =
    useStudioStore();

  useEffect(() => {
    if (projectId) return;

    const saved = loadStudioProject();
    if (!saved?.projectId) return;

    restoreProject(saved);
    addLog(`Restored last project: ${saved.projectName}`);
  }, [projectId, restoreProject, addLog]);

  return (
    <>
      <div className="grid gap-6 lg:grid-cols-12">
        <aside className="space-y-6 lg:col-span-3">
          <section className="rounded-2xl border border-border/70 bg-card p-4">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Upload
            </h2>
            <ModelUploadPanel />
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
