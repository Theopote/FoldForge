"use client";

import { Download, FileImage, FileText, Loader2, Package } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useStudioStore } from "@/store/studio-store";

export function UnfoldPreviewPanel() {
  const { unfoldSvgUrl, unfoldPdfUrl, unfoldZipUrl, status } = useStudioStore();
  const isProcessing = status === "processing";

  return (
    <Card className="flex h-full min-h-[420px] flex-col border-border/70 shadow-none">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">2D Unfold Preview</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col">
        <div className="relative flex flex-1 items-center justify-center overflow-hidden rounded-2xl border border-dashed border-border bg-[linear-gradient(45deg,#f8fafc_25%,transparent_25%),linear-gradient(-45deg,#f8fafc_25%,transparent_25%),linear-gradient(45deg,transparent_75%,#f8fafc_75%),linear-gradient(-45deg,transparent_75%,#f8fafc_75%)] bg-[length:16px_16px] bg-[position:0_0,0_8px,8px_-8px,-8px_0px]">
          {isProcessing && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-white/80 backdrop-blur-sm">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="text-sm font-medium">Generating unfold template…</p>
              <p className="text-xs text-muted-foreground">
                Cleaning mesh · unfolding · layout · export
              </p>
            </div>
          )}

          {!isProcessing && unfoldSvgUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={`${unfoldSvgUrl}?t=${Date.now()}`}
              alt="Unfold preview"
              className="max-h-full max-w-full object-contain p-4"
            />
          ) : !isProcessing ? (
            <div className="px-6 text-center">
              <FileImage className="mx-auto mb-3 h-10 w-10 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                Generate a template to see the unfold layout here.
              </p>
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
        <a href={url} download={downloadName} target="_blank" rel="noopener noreferrer">
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
