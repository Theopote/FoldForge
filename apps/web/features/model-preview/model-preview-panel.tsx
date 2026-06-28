"use client";

import { useCallback, useEffect, useState } from "react";
import { Box, Flame, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ModelViewer } from "@/features/model-preview/model-viewer";
import { useSeamManifest } from "@/features/unfold-preview/use-seam-manifest";
import type { ModelMeshStats } from "@/lib/geometry-stats";
import { useStudioStore } from "@/store/studio-store";

export function ModelPreviewPanel() {
  const {
    projectId,
    sourceFileUrl,
    processedModelUrl,
    sourceType,
    aiProvider,
    status,
    exportRevision,
    meshStats,
    stats,
    craftability,
    selectedSeamMeshEdge,
    selectedSeamHighlight,
    seamInspectorMode,
    showOverlapHeatmap,
    setShowOverlapHeatmap,
    setSelectedSeamHighlight,
    setMeshStats,
    addLog,
    setError,
  } = useStudioStore();
  const [isLoadingModel, setIsLoadingModel] = useState(false);

  const previewUrl =
    status === "ready" && processedModelUrl ? processedModelUrl : sourceFileUrl;

  const seamManifest = useSeamManifest(
    projectId,
    exportRevision,
    seamInspectorMode && status === "ready",
  );

  useEffect(() => {
    if (previewUrl) {
      setIsLoadingModel(true);
    }
  }, [previewUrl]);

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

  const handleSeamSelect = useCallback(
    (meshEdge: string) => {
      const edge = seamManifest?.edges[meshEdge];
      setSelectedSeamHighlight({
        meshEdge,
        position3d: edge?.position3d ?? null,
      });
      addLog(`Selected seam edge ${meshEdge} from 3D view`);
    },
    [seamManifest, setSelectedSeamHighlight, addLog],
  );

  const faceHeat = seamManifest?.advisor?.faceHeat ?? null;
  const hasHeatmap = Boolean(faceHeat && Object.keys(faceHeat).length > 0);

  return (
    <Card className="flex h-full min-h-[420px] flex-col border-border/70 shadow-none">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Box className="h-4 w-4 text-primary" />
          3D Preview
        </CardTitle>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Badge variant="outline" className="text-xs capitalize">
            {sourceType.replace(/_/g, " ")}
          </Badge>
          {aiProvider && (
            <Badge variant="outline" className="text-xs">
              AI: {aiProvider}
            </Badge>
          )}
          {seamInspectorMode && (
            <Badge
              variant={showOverlapHeatmap ? "default" : "outline"}
              className="cursor-pointer gap-1 text-xs"
              onClick={() => setShowOverlapHeatmap(!showOverlapHeatmap)}
            >
              <Flame className="h-3 w-3" />
              Heatmap
            </Badge>
          )}
          {selectedSeamMeshEdge && (
            <Badge variant="secondary" className="text-xs">
              Seam {selectedSeamMeshEdge}
            </Badge>
          )}
          <Badge variant="outline" className="text-xs">
            Craftability: {craftability ? `${craftability.score}` : "—"}
          </Badge>
          <Badge variant="secondary">{status}</Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col">
        <div className="relative flex flex-1 flex-col overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-sky-50/80 via-white to-orange-50/80">
          {previewUrl ? (
            <>
              {isLoadingModel && (
                <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/60">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              )}
              {seamInspectorMode && (
                <p className="absolute left-3 right-3 top-3 z-10 rounded-lg border border-border/70 bg-background/90 px-3 py-1.5 text-center text-[11px] text-muted-foreground backdrop-blur-sm">
                  {hasHeatmap && showOverlapHeatmap
                    ? "Orange faces show unfold overlap intensity · click an edge to inspect"
                    : "Click a seam edge in 3D or the 2D unfold to inspect and edit"}
                </p>
              )}
              <ModelViewer
                url={previewUrl}
                onLoaded={handleLoaded}
                onError={handleError}
                seamHighlight={selectedSeamHighlight}
                seamEdges={seamInspectorMode ? (seamManifest?.edges ?? null) : null}
                seamPickEnabled={seamInspectorMode && Boolean(seamManifest?.edges)}
                selectedSeamMeshEdge={selectedSeamMeshEdge}
                onSeamSelect={handleSeamSelect}
                faceHeat={faceHeat}
                showHeatmap={showOverlapHeatmap && hasHeatmap}
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
          <Metric label="Faces" value={stats?.faces ?? meshStats?.faces ?? "—"} />
          <Metric label="Pieces" value={stats?.pieces ?? "—"} />
          <Metric label="Pages" value={stats?.pages ?? "—"} />
          <Metric label="Vertices" value={meshStats?.vertices ?? "—"} />
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
