"use client";

import { useCallback, useState } from "react";

import { reflowProjectSeams } from "@/lib/api";
import { useStudioStore } from "@/store/studio-store";

export function useSeamReflow(projectId: string | null) {
  const {
    completePapercraftProcessing,
    setJobProgress,
    clearJobProgress,
    setError,
    addLog,
  } = useStudioStore();
  const [undoStack, setUndoStack] = useState<string[]>([]);
  const [pending, setPending] = useState(false);
  const [seamError, setSeamError] = useState<string | null>(null);

  const runReflow = useCallback(
    async (
      payload: { toggle: { meshEdge: string } } | { seams: string[] },
      options?: { recordUndo?: boolean; meshEdgeForUndo?: string },
    ) => {
      if (!projectId || pending) {
        return;
      }

      setPending(true);
      setSeamError(null);
      addLog("Updating seams and re-unfolding…");

      try {
        const result = await reflowProjectSeams(projectId, payload, {
          onProgress: (job) => {
            setJobProgress({
              phase: "papercraft_process",
              progress: job.progress ?? 0,
              message: job.message ?? "Re-unfolding…",
            });
          },
        });

        if (options?.recordUndo !== false && options?.meshEdgeForUndo) {
          setUndoStack((stack) => [...stack, options.meshEdgeForUndo!]);
        }

        completePapercraftProcessing({
          processedModelUrl: result.processedModelUrl ?? null,
          unfoldSvgUrl: result.unfoldSvgUrl ?? null,
          unfoldPdfUrl: result.unfoldPdfUrl ?? null,
          unfoldZipUrl: result.unfoldZipUrl ?? null,
          stats: result.stats ?? null,
          craftability: result.craftability ?? null,
          status: "ready",
        });
        addLog("Seam update complete.");
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Seam update failed.";
        setSeamError(message);
        setError(message);
        addLog(`Seam update failed: ${message}`);
      } finally {
        setPending(false);
        clearJobProgress();
      }
    },
    [
      projectId,
      pending,
      completePapercraftProcessing,
      setJobProgress,
      clearJobProgress,
      setError,
      addLog,
    ],
  );

  const toggleSeam = useCallback(
    async (meshEdge: string) => {
      await runReflow({ toggle: { meshEdge } }, { meshEdgeForUndo: meshEdge });
    },
    [runReflow],
  );

  const undoSeam = useCallback(async () => {
    const meshEdge = undoStack[undoStack.length - 1];
    if (!meshEdge) {
      return;
    }
    setUndoStack((stack) => stack.slice(0, -1));
    await runReflow(
      { toggle: { meshEdge } },
      { recordUndo: false, meshEdgeForUndo: meshEdge },
    );
  }, [runReflow, undoStack]);

  return {
    toggleSeam,
    undoSeam,
    canUndo: undoStack.length > 0,
    pending,
    seamError,
  };
}
