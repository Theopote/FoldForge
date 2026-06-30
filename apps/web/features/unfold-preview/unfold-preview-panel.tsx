"use client";

import { useState } from "react";
import { Download, FileImage, FileText, Flame, Loader2, MousePointer2, Package, Palette } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { withStorageAuth } from "@/lib/api-auth";
import {
  UnfoldSvgPreview,
  type UnfoldPreviewLayer,
} from "@/features/unfold-preview/unfold-svg-preview";
import { useSeamManifest } from "@/features/unfold-preview/use-seam-manifest";
import { useSeamReflow } from "@/features/unfold-preview/use-seam-reflow";
import { useStudioStore } from "@/store/studio-store";

export function UnfoldPreviewPanel() {
  const {
    projectId,
    unfoldSvgUrl,
    unfoldPdfUrl,
    unfoldZipUrl,
    status,
    settings,
    exportRevision,
    exportedColorMode,
    seamInspectorMode,
    showOverlapHeatmap,
    setSeamInspectorMode,
    setShowOverlapHeatmap,
  } = useStudioStore();
  const [previewLayer, setPreviewLayer] = useState<UnfoldPreviewLayer>("both");
  const seamManifest = useSeamManifest(
    projectId,
    exportRevision,
    seamInspectorMode && status === "ready",
  );
  const { toggleSeam, undoSeam, canUndo, pending: seamPending, seamError } =
    useSeamReflow(projectId);
  const isProcessing = status === "processing" || seamPending;
  const previewIsColor = exportedColorMode === "color";
  const previewIsStale =
    status === "ready" &&
    unfoldSvgUrl !== null &&
    exportedColorMode !== null &&
    settings.colorMode !== exportedColorMode;

  return (
    <Card className="flex h-full min-h-[420px] flex-col border-border/70 shadow-none">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base">2D Unfold Preview</CardTitle>
          {previewIsColor && unfoldSvgUrl && !isProcessing && (
            <Badge variant="secondary" className="gap-1 font-normal">
              <Palette className="h-3 w-3" />
              Color
            </Badge>
          )}
        </div>
        {previewIsColor && unfoldSvgUrl && !isProcessing && (
          <div className="flex flex-wrap gap-2 pt-1">
            <LayerToggle
              label="Both"
              active={previewLayer === "both" && !seamInspectorMode}
              onClick={() => {
                setSeamInspectorMode(false);
                setPreviewLayer("both");
              }}
            />
            <LayerToggle
              label="Baked"
              active={previewLayer === "color" && !seamInspectorMode}
              onClick={() => {
                setSeamInspectorMode(false);
                setPreviewLayer("color");
              }}
            />
            <LayerToggle
              label="Lines"
              active={previewLayer === "lines" && !seamInspectorMode}
              onClick={() => {
                setSeamInspectorMode(false);
                setPreviewLayer("lines");
              }}
            />
          </div>
        )}
        {unfoldSvgUrl && !isProcessing && (
          <div className="flex flex-wrap gap-2 pt-1">
            <LayerToggle
              label="Seams"
              active={seamInspectorMode}
              onClick={() => setSeamInspectorMode(!seamInspectorMode)}
              icon={MousePointer2}
            />
            {seamInspectorMode && (
              <LayerToggle
                label="Heatmap"
                active={showOverlapHeatmap}
                onClick={() => setShowOverlapHeatmap(!showOverlapHeatmap)}
                icon={Flame}
              />
            )}
          </div>
        )}
        {previewIsStale && (
          <p className="text-xs text-amber-700">
            Color mode changed — regenerate the template to refresh the preview.
          </p>
        )}
      </CardHeader>
      <CardContent className="flex flex-1 flex-col">
        <div
          className={
            unfoldSvgUrl && !isProcessing
              ? "relative flex flex-1 items-center justify-center overflow-hidden rounded-2xl border border-border bg-white"
              : "relative flex flex-1 items-center justify-center overflow-hidden rounded-2xl border border-dashed border-border bg-[linear-gradient(45deg,#f8fafc_25%,transparent_25%),linear-gradient(-45deg,#f8fafc_25%,transparent_25%),linear-gradient(45deg,transparent_75%,#f8fafc_75%),linear-gradient(-45deg,transparent_75%,#f8fafc_75%)] bg-[length:16px_16px] bg-[position:0_0,0_8px,8px_-8px,-8px_0px]"
          }
        >
          {isProcessing && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-white/80 backdrop-blur-sm">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="text-sm font-medium">
                {seamPending ? "Re-unfolding after seam edit…" : "Generating unfold template…"}
              </p>
              <p className="text-xs text-muted-foreground">
                {seamPending
                  ? "Updating patches · tabs · layout · export"
                  : settings.colorMode === "color"
                    ? "Cleaning mesh · unfolding · baking colors · layout · export"
                    : "Cleaning mesh · unfolding · layout · export"}
              </p>
            </div>
          )}

          {!isProcessing && unfoldSvgUrl ? (
            <UnfoldSvgPreview
              url={unfoldSvgUrl}
              revision={exportRevision}
              layer={seamInspectorMode ? "lines" : previewLayer}
              className="p-4"
              seamInspector={seamInspectorMode}
              manifest={seamManifest}
              onToggleSeam={toggleSeam}
              onUndoSeam={undoSeam}
              canUndoSeam={canUndo}
              seamReflowPending={seamPending}
              seamError={seamError}
            />
          ) : !isProcessing ? (
            <div className="px-6 text-center">
              <FileImage className="mx-auto mb-3 h-10 w-10 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                Generate a template to see the unfold layout here.
              </p>
              {settings.colorMode === "color" && (
                <p className="mt-2 text-xs text-muted-foreground">
                  Color mode is on — surface colors will appear after generation.
                </p>
              )}
            </div>
          ) : null}
        </div>

        <ExportPanel
          disabled={status !== "ready"}
          svgUrl={unfoldSvgUrl}
          pdfUrl={unfoldPdfUrl}
          zipUrl={unfoldZipUrl}
          projectReady={status === "ready"}
        />
      </CardContent>
    </Card>
  );
}

function LayerToggle({
  label,
  active,
  onClick,
  icon: Icon,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <Badge
      variant={active ? "default" : "outline"}
      className="cursor-pointer gap-1 font-normal"
      onClick={onClick}
    >
      {Icon && <Icon className="h-3 w-3" />}
      {label}
    </Badge>
  );
}

function ExportPanel({
  disabled,
  svgUrl,
  pdfUrl,
  zipUrl,
  projectReady,
}: {
  disabled: boolean;
  svgUrl: string | null;
  pdfUrl: string | null;
  zipUrl: string | null;
  projectReady: boolean;
}) {
  return (
    <div className="mt-4 space-y-2">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Download
      </p>
      <div className="grid grid-cols-1 gap-2">
        <DownloadButton
          label="Export PDF"
          icon={FileText}
          url={pdfUrl}
          disabled={disabled}
          downloadName="unfold.pdf"
        />
        <DownloadButton
          label="Export SVG"
          icon={Download}
          url={svgUrl}
          disabled={disabled}
          downloadName="unfold.svg"
        />
        <DownloadButton
          label={projectReady ? "Download Kit (ZIP)" : "Export ZIP"}
          icon={Package}
          url={zipUrl}
          disabled={disabled}
          downloadName="papercraft-kit.zip"
          primary={projectReady}
        />
      </div>
    </div>
  );
}

function DownloadButton({
  label,
  icon: Icon,
  url,
  disabled,
  downloadName,
  primary = false,
}: {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  url: string | null;
  disabled: boolean;
  downloadName: string;
  primary?: boolean;
}) {
  if (url) {
    return (
      <Button
        variant={primary ? "default" : "outline"}
        className="justify-start"
        asChild
      >
        <a
          href={withStorageAuth(url)}
          download={downloadName}
          target="_blank"
          rel="noopener noreferrer"
        >
          <Icon className="mr-2 h-4 w-4" />
          {label}
        </a>
      </Button>
    );
  }

  return (
    <Button variant="outline" disabled={disabled} className="justify-start">
      <Icon className="mr-2 h-4 w-4" />
      {label}
    </Button>
  );
}
