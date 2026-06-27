"use client";

import { useCallback, useEffect, useState } from "react";
import { Box, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ModelViewer } from "@/features/model-preview/model-viewer";
import type { ModelMeshStats } from "@/lib/geometry-stats";
import { useStudioStore } from "@/store/studio-store";

export function ModelPreviewPanel() {
  const {
    sourceFileUrl,
    status,
    meshStats,
    stats,
    setMeshStats,
    addLog,
    setError,
  } = useStudioStore();
  const [isLoadingModel, setIsLoadingModel] = useState(false);

  useEffect(() => {
    if (sourceFileUrl) {
      setIsLoadingModel(true);
    }
  }, [sourceFileUrl]);

  const handleLoaded = useCallback(
    (loadedStats: ModelMeshStats) => {
      setMeshStats(loadedStats);
      setIsLoadingModel(false);
      addLog(
        `3D preview loaded — ${loadedStats.faces} faces, ${loadedStats.vertices} vertices`,
      );
    },
    [addLog, setMeshStats],
  );

  const handleError = useCallback(
    (message: string) => {
      setIsLoadingModel(false);
      setError(message);
      addLog(`3D preview error: ${message}`);
    },
    [addLog, setError],
  );

  return (
    <Card className="flex h-full min-h-[420px] flex-col border-border/70 shadow-none">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Box className="h-4 w-4 text-primary" />
          3D Preview
        </CardTitle>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">
            Craftability: —
          </Badge>
          <Badge variant="secondary">{status}</Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col">
        <div className="relative flex flex-1 flex-col overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-sky-50/80 via-white to-orange-50/80">
          {sourceFileUrl ? (
            <>
              {isLoadingModel && (
                <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/60">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              )}
              <ModelViewer
                url={sourceFileUrl}
                onLoaded={handleLoaded}
                onError={handleError}
              />
            </>
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
              <Box className="mb-4 h-12 w-12 text-primary/40" />
              <p className="text-sm font-medium text-foreground/80">
                Upload a model to preview
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Drag to rotate · Scroll to zoom · Right-drag to pan
              </p>
            </div>
          )}
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Metric label="Faces" value={meshStats?.faces ?? stats?.faces ?? "—"} />
          <Metric label="Vertices" value={meshStats?.vertices ?? "—"} />
          <Metric label="Edges" value={meshStats?.edges ?? "—"} />
          <Metric
            label="Size (mm)"
            value={
              meshStats
                ? `${meshStats.widthMm}×${meshStats.heightMm}×${meshStats.depthMm}`
                : "—"
            }
          />
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl bg-muted/40 px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-semibold tabular-nums">{value}</p>
    </div>
  );
}
