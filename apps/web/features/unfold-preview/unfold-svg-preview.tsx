"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { unfoldPreviewUrl } from "@/lib/unfold-preview-url";
import {
  formatSeamTooltip,
  readSeamLineMetadata,
  parseSeamManifest,
  seamManifestPreviewUrl,
  type SeamManifest,
  type SeamSuggestion,
} from "@/lib/seam-manifest";
import { useStudioStore } from "@/store/studio-store";

export type UnfoldPreviewLayer = "both" | "color" | "lines";

const PREVIEW_LAYER_STYLES = `
.unfold-preview-color-only .layer-lines,
.unfold-preview-color-only .layer-seams {
  display: none;
}
.unfold-preview-lines-only .layer-baked {
  display: none;
}
.unfold-svg-host:not(.unfold-seam-inspector) .layer-seams {
  display: none;
}
.unfold-seam-inspector .layer-seams .seam-edge {
  cursor: crosshair;
  pointer-events: stroke;
}
.unfold-seam-inspector .layer-seams .seam-cut:hover,
.unfold-seam-inspector .layer-seams .seam-cut.seam-selected {
  stroke: rgba(232, 93, 76, 0.85);
  stroke-width: 0.65mm;
}
.unfold-seam-inspector .layer-seams .seam-fold:hover,
.unfold-seam-inspector .layer-seams .seam-fold.seam-selected {
  stroke: rgba(37, 99, 235, 0.75);
  stroke-width: 0.55mm;
}
.unfold-seam-inspector .piece-has-overlap .layer-lines polygon,
.unfold-seam-inspector .piece-has-overlap .layer-lines line {
  filter: drop-shadow(0 0 0.4mm rgba(234, 88, 12, 0.55));
}
.unfold-svg-host svg {
  display: block;
  height: auto;
  max-height: 100%;
  max-width: 100%;
  width: auto;
}
`;

type SelectedSeam = {
  meshEdge: string;
  pieceLabel: string;
  edgeKind: string;
  foldType: string | null;
  tooltip: string;
  suggestions: SeamSuggestion[];
};

export function UnfoldSvgPreview({
  url,
  revision,
  layer,
  className = "",
  seamInspector = false,
  projectId = null,
  onToggleSeam,
  onUndoSeam,
  canUndoSeam = false,
  seamReflowPending = false,
  seamError = null,
}: {
  url: string;
  revision: number;
  layer: UnfoldPreviewLayer;
  className?: string;
  seamInspector?: boolean;
  projectId?: string | null;
  onToggleSeam?: (meshEdge: string) => void | Promise<void>;
  onUndoSeam?: () => void | Promise<void>;
  canUndoSeam?: boolean;
  seamReflowPending?: boolean;
  seamError?: string | null;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const setSelectedSeamHighlight = useStudioStore(
    (state) => state.setSelectedSeamHighlight,
  );
  const [markup, setMarkup] = useState<string | null>(null);
  const [manifest, setManifest] = useState<SeamManifest | null>(null);
  const [selectedSeam, setSelectedSeam] = useState<SelectedSeam | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setMarkup(null);
    setManifest(null);
    setSelectedSeam(null);
    setError(false);

    void fetch(unfoldPreviewUrl(url, revision))
      .then((response) => {
        if (!response.ok) {
          throw new Error("preview fetch failed");
        }
        return response.text();
      })
      .then((text) => {
        if (!cancelled) {
          setMarkup(text);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError(true);
        }
      });

    if (seamInspector && projectId) {
      void fetch(seamManifestPreviewUrl(projectId, revision))
        .then((response) => (response.ok ? response.json() : null))
        .then((payload) => {
          if (!cancelled && payload) {
            setManifest(parseSeamManifest(payload));
          }
        })
        .catch(() => {
          /* manifest is optional for older exports */
        });
    }

    return () => {
      cancelled = true;
    };
  }, [url, revision, seamInspector, projectId]);

  const handleSeamClick = useCallback(
    (event: Event) => {
      const target = event.currentTarget as SVGLineElement;
      const meta = readSeamLineMetadata(target);
      if (!meta.meshEdge) {
        return;
      }

      hostRef.current
        ?.querySelectorAll(".seam-edge.seam-selected")
        .forEach((node) => node.classList.remove("seam-selected"));
      target.classList.add("seam-selected");

      const manifestEdge = manifest?.edges[meta.meshEdge];
      const edgeHint = manifest?.advisor?.edgeHints[meta.meshEdge];

      setSelectedSeamHighlight({
        meshEdge: meta.meshEdge,
        position3d: manifestEdge?.position3d ?? null,
      });

      setSelectedSeam({
        meshEdge: meta.meshEdge,
        pieceLabel: meta.pieceLabel,
        edgeKind: meta.edgeKind,
        foldType: meta.foldType,
        tooltip: formatSeamTooltip(
          meta.meshEdge,
          {
            pieceLabel: meta.pieceLabel,
            edgeKind: meta.edgeKind,
            foldType: meta.foldType,
          },
          manifestEdge,
          edgeHint,
        ),
        suggestions: manifest?.advisor?.suggestions ?? [],
      });
    },
    [manifest, setSelectedSeamHighlight],
  );

  useEffect(() => {
    if (!seamInspector || !markup || !hostRef.current) {
      return;
    }

    const edges = hostRef.current.querySelectorAll<SVGLineElement>(".seam-edge");
    edges.forEach((edge) => {
      edge.addEventListener("click", handleSeamClick);
    });

    return () => {
      edges.forEach((edge) => {
        edge.removeEventListener("click", handleSeamClick);
      });
    };
  }, [markup, seamInspector, handleSeamClick]);

  const layerClass =
    layer === "color"
      ? "unfold-preview-color-only"
      : layer === "lines"
        ? "unfold-preview-lines-only"
        : "unfold-preview-both";

  if (error) {
    return (
      <p className="px-6 text-center text-sm text-destructive">
        Failed to load unfold preview.
      </p>
    );
  }

  if (!markup) {
    return null;
  }

  return (
    <>
      <style>{PREVIEW_LAYER_STYLES}</style>
      <div className="relative flex h-full w-full flex-col">
        <div
          ref={hostRef}
          className={`unfold-svg-host flex flex-1 items-center justify-center ${layerClass} ${
            seamInspector ? "unfold-seam-inspector" : ""
          } ${className}`}
          dangerouslySetInnerHTML={{ __html: markup }}
        />
        {seamInspector && selectedSeam && (
          <div className="absolute bottom-3 left-3 right-3 rounded-xl border border-border bg-background/95 p-3 text-xs shadow-sm backdrop-blur-sm">
            <p className="font-medium text-foreground">
              {selectedSeam.edgeKind === "fold" ? "Fold line" : "Cut seam"} · Piece{" "}
              {selectedSeam.pieceLabel || "—"}
            </p>
            <pre className="mt-1 whitespace-pre-wrap text-muted-foreground">
              {selectedSeam.tooltip}
            </pre>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button
                size="sm"
                disabled={
                  seamReflowPending ||
                  !onToggleSeam ||
                  manifest?.advisor?.edgeHints[selectedSeam.meshEdge]?.toggleValid ===
                    false
                }
                onClick={() => void onToggleSeam?.(selectedSeam.meshEdge)}
              >
                {selectedSeam.edgeKind === "fold" ? "Split here" : "Merge pieces"}
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={seamReflowPending || !canUndoSeam || !onUndoSeam}
                onClick={() => void onUndoSeam?.()}
              >
                Undo
              </Button>
            </div>
            {seamError && (
              <p className="mt-2 text-destructive">{seamError}</p>
            )}
            {selectedSeam.suggestions.length > 0 && (
              <div className="mt-3 border-t border-border pt-2">
                <p className="font-medium text-foreground">Suggested seams</p>
                <ul className="mt-1 space-y-1 text-muted-foreground">
                  {selectedSeam.suggestions.slice(0, 3).map((item) => (
                    <li key={item.meshEdge}>
                      {item.label} ({item.meshEdge})
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {manifest?.advisor?.overlapPieces.length ? (
              <p className="mt-2 text-amber-700">
                Overlapping pieces: {manifest.advisor.overlapPieces.join(", ")}
              </p>
            ) : null}
          </div>
        )}
        {seamInspector && !selectedSeam && (
          <p className="absolute bottom-3 left-3 right-3 rounded-xl border border-dashed border-border bg-background/90 px-3 py-2 text-center text-xs text-muted-foreground backdrop-blur-sm">
            Click a cut edge or fold line to inspect seam geometry.
          </p>
        )}
      </div>
    </>
  );
}
