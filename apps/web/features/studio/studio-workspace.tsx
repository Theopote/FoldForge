"use client";

import { useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { CraftabilityCard } from "@/features/craftability/craftability-card";
import { ProcessingLogPanel } from "@/features/export-panel/processing-log-panel";
import { ModelPreviewPanel } from "@/features/model-preview/model-preview-panel";
import { CreateSourcePanel } from "@/features/model-upload/create-source-panel";
import { ProjectSettingsPanel } from "@/features/project-settings/project-settings-panel";
import { UnfoldPreviewPanel } from "@/features/unfold-preview/unfold-preview-panel";
import { cancelAllJobPolls } from "@/lib/job-poll-session";
import {
  STUDIO_SESSION_STORAGE_KEY,
  clearLastProjectId,
  loadLastProjectId,
  resolveStudioProjectId,
} from "@/lib/project-storage";
import { hydrateStudioProject } from "@/lib/studio-hydration";
import { useStudioStore } from "@/store/studio-store";

export function StudioWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlProjectId = searchParams.get("project");

  const { projectId, status, craftability, addLog } = useStudioStore();
  const hydratingRef = useRef<string | null>(null);
  const prevUrlProjectIdRef = useRef<string | null>(urlProjectId);

  const runHydration = (targetId: string, logLabel: string) => {
    if (hydratingRef.current === targetId) return;

    hydratingRef.current = targetId;
    let cancelled = false;

    void (async () => {
      const result = await hydrateStudioProject(targetId);
      if (cancelled) return;

      hydratingRef.current = null;

      if (result === "ok") {
        addLog(`${logLabel}: ${useStudioStore.getState().projectName}`);
        return;
      }

      if (result === "not_found") {
        clearLastProjectId();
        router.replace("/studio");
        addLog("Previous project no longer exists — starting fresh.");
        return;
      }

      addLog("Could not reach the server — open Studio again when the API is running.");
    })();

    return () => {
      cancelled = true;
      cancelAllJobPolls();
    };
  };

  // Keep the URL in sync when the in-memory project changes (upload / AI create).
  useEffect(() => {
    if (!projectId || projectId === urlProjectId) return;
    router.replace(`/studio?project=${encodeURIComponent(projectId)}`, {
      scroll: false,
    });
  }, [projectId, urlProjectId, router]);

  // Initial open: store empty → load from ?project= or last local id.
  useEffect(() => {
    if (projectId) return;

    const targetId = resolveStudioProjectId(urlProjectId, loadLastProjectId());
    if (!targetId) return;

    return runHydration(targetId, "Restored project");
  }, [projectId, urlProjectId, addLog, router]);

  // Explicit navigation to /studio?project=other while another project is loaded.
  useEffect(() => {
    if (urlProjectId === prevUrlProjectIdRef.current) return;
    prevUrlProjectIdRef.current = urlProjectId;

    if (!urlProjectId || urlProjectId === projectId) return;

    return runHydration(urlProjectId, "Opened project");
  }, [urlProjectId, projectId, addLog, router]);

  // Another tab switched the last project id.
  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key !== STUDIO_SESSION_STORAGE_KEY || !event.newValue) return;

      try {
        const parsed = JSON.parse(event.newValue) as { projectId?: unknown };
        const nextId =
          typeof parsed.projectId === "string" ? parsed.projectId : null;
        if (!nextId || nextId === useStudioStore.getState().projectId) return;

        router.replace(`/studio?project=${encodeURIComponent(nextId)}`, {
          scroll: false,
        });
      } catch {
        // Ignore malformed cross-tab payloads.
      }
    };

    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [router]);

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
