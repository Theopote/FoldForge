"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { unfoldPreviewUrl } from "@/lib/unfold-preview-url";
import {
  formatSeamTooltip,
  readSeamLineMetadata,
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

type MarkupState = {
  key: string;
  markup: string | null;
  error: boolean;
};

export function UnfoldSvgPreview({
  url,
  revision,
  layer,
  className = "",
  seamInspector = false,
  manifest = null,
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
  manifest?: SeamManifest | null;
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
  const selectedSeamMeshEdge = useStudioStore(
    (state) => state.selectedSeamMeshEdge,
  );
  const previewKey = `${url}:${revision}`;
  const [markupState, setMarkupState] = useState<MarkupState | null>(null);
  const [selectedSeam, setSelectedSeam] = useState<SelectedSeam | null>(null);
  const markup = markupState?.key === previewKey ? markupState.markup : null;
  const error = markupState?.key === previewKey ? markupState.error : false;

  const selectSeam = useCallback(
    (
      meshEdge: string,
      attrs: {
        pieceLabel?: string | null;
        edgeKind?: string | null;
        foldType?: string | null;
      },
    ) => {
      const manifestEdge = manifest?.edges[meshEdge];
      const edgeHint = manifest?.advisor?.edgeHints[meshEdge];

      hostRef.current
        ?.querySelectorAll(".seam-edge.seam-selected")
        .forEach((node) => node.classList.remove("seam-selected"));

      const [v0, v1] = meshEdge.split(",");
      const svgEdge =
        hostRef.current?.querySelector<SVGLineElement>(
          `.seam-edge[id$="-${v0}-${v1}"], .seam-edge[id$="-${v1}-${v0}"]`,
        ) ?? null;
      svgEdge?.classList.add("seam-selected");

      setSelectedSeamHighlight({
        meshEdge,
        position3d: manifestEdge?.position3d ?? null,
      });

      setSelectedSeam({
        meshEdge,
        pieceLabel: attrs.pieceLabel ?? manifestEdge?.pieceLabel ?? "",
        edgeKind: attrs.edgeKind ?? manifestEdge?.kind ?? "cut",
        foldType: attrs.foldType ?? manifestEdge?.foldType ?? null,
        tooltip: formatSeamTooltip(
          meshEdge,
          {
            pieceLabel: attrs.pieceLabel ?? manifestEdge?.pieceLabel,
            edgeKind: attrs.edgeKind ?? manifestEdge?.kind,
            foldType: attrs.foldType ?? manifestEdge?.foldType,
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
    let cancelled = false;

    void fetch(unfoldPreviewUrl(url, revision))
      .then((response) => {
        if (!response.ok) {
          throw new Error("preview fetch failed");
        }
        return response.text();
      })
      .then((text) => {
        if (!cancelled) {
          setMarkupState({ key: previewKey, markup: text, error: false });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setMarkupState({ key: previewKey, markup: null, error: true });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [url, revision, previewKey]);

  useEffect(() => {
    if (!seamInspector || !selectedSeamMeshEdge || !manifest || !markup) {
      return;
    }
    if (selectedSeam?.meshEdge === selectedSeamMeshEdge) {
      return;
    }
    queueMicrotask(() => {
      selectSeam(selectedSeamMeshEdge, {});
    });
  }, [
    seamInspector,
    selectedSeamMeshEdge,
    manifest,
    markup,
    selectSeam,
    selectedSeam?.meshEdge,
  ]);

  const handleSeamClick = useCallback(
    (event: Event) => {
      const target = event.currentTarget as SVGLineElement;
      const meta = readSeamLineMetadata(target);
      if (!meta.meshEdge) {
        return;
      }

      selectSeam(meta.meshEdge, {
        pieceLabel: meta.pieceLabel,
        edgeKind: meta.edgeKind,
        foldType: meta.foldType,
      });
    },
    [selectSeam],
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
              {selectedSeam.edgeKind === "fold" ? "Fold line" : "Cut seam"} - Piece{" "}
              {selectedSeam.pieceLabel || "-"}
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
                <ul className="mt-1 space-y-2 text-muted-foreground">
                  {selectedSeam.suggestions.slice(0, 3).map((item) => (
                    <SuggestionRow
                      key={item.meshEdge}
                      item={item}
                      disabled={
                        seamReflowPending ||
                        !onToggleSeam ||
                        manifest?.advisor?.edgeHints[item.meshEdge]?.toggleValid ===
                          false
                      }
                      onApply={() => void onToggleSeam?.(item.meshEdge)}
                    />
                  ))}
                </ul>
              </div>
            )}
            {manifest?.advisor?.guidance?.length ? (
              <div className="mt-3 border-t border-border pt-2">
                <p className="font-medium text-foreground">Seam advisor</p>
                <ul className="mt-1 list-disc space-y-1 pl-4 text-muted-foreground">
                  {manifest.advisor.guidance.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {manifest?.advisor?.overlapPieces.length ? (
              <p className="mt-2 text-amber-700">
                Overlapping pieces: {manifest.advisor.overlapPieces.join(", ")}
              </p>
            ) : null}
          </div>
        )}
        {seamInspector && !selectedSeam && (
          <p className="absolute bottom-3 left-3 right-3 rounded-xl border border-dashed border-border bg-background/90 px-3 py-2 text-center text-xs text-muted-foreground backdrop-blur-sm">
            Click a cut edge or fold line in 2D or 3D to inspect seam geometry.
          </p>
        )}
      </div>
    </>
  );
}

function SuggestionRow({
  item,
  disabled,
  onApply,
}: {
  item: SeamSuggestion;
  disabled: boolean;
  onApply: () => void;
}) {
  return (
    <li className="rounded-lg border border-border/70 bg-muted/20 p-2">
      <p className="text-foreground">{item.label}</p>
      {item.reason && <p className="mt-0.5 text-[11px]">{item.reason}</p>}
      <div className="mt-2 flex items-center justify-between gap-2">
        <span className="text-[11px]">{item.meshEdge}</span>
        <Button size="sm" variant="secondary" disabled={disabled} onClick={onApply}>
          Apply
        </Button>
      </div>
    </li>
  );
}
