"use client";

import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";

import type { ModelMeshStats } from "@/lib/geometry-stats";
import type { SeamEdgeInfo, SeamPosition3d } from "@/lib/seam-manifest";

const ModelViewerCanvas = dynamic(
  () =>
    import("./model-viewer-canvas").then((mod) => mod.ModelViewerCanvas),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    ),
  },
);

type ModelViewerProps = {
  url: string;
  onLoaded: (stats: ModelMeshStats) => void;
  onError: (message: string) => void;
  seamHighlight?: SeamPosition3d | null;
  seamEdges?: Record<string, SeamEdgeInfo> | null;
  seamPickEnabled?: boolean;
  selectedSeamMeshEdge?: string | null;
  onSeamSelect?: (meshEdge: string) => void;
  faceHeat?: Record<string, number> | null;
  showHeatmap?: boolean;
};

export function ModelViewer({
  url,
  onLoaded,
  onError,
  seamHighlight = null,
  seamEdges = null,
  seamPickEnabled = false,
  selectedSeamMeshEdge = null,
  onSeamSelect,
  faceHeat = null,
  showHeatmap = false,
}: ModelViewerProps) {
  return (
    <div className="h-full min-h-[320px] w-full overflow-hidden rounded-2xl">
      <ModelViewerCanvas
        url={url}
        onLoaded={onLoaded}
        onError={onError}
        seamHighlight={seamHighlight}
        seamEdges={seamEdges}
        seamPickEnabled={seamPickEnabled}
        selectedSeamMeshEdge={selectedSeamMeshEdge}
        onSeamSelect={onSeamSelect}
        faceHeat={faceHeat}
        showHeatmap={showHeatmap}
      />
    </div>
  );
}
