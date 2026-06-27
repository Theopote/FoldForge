"use client";

import { Download, FileImage, FileText, Package } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useStudioStore } from "@/store/studio-store";

export function UnfoldPreviewPanel() {
  const { unfoldSvgUrl, status } = useStudioStore();

  return (
    <Card className="flex h-full min-h-[420px] flex-col border-border/70 shadow-none">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">2D Unfold Preview</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col">
        <div className="flex flex-1 items-center justify-center rounded-2xl border border-dashed border-border bg-[linear-gradient(45deg,#f8fafc_25%,transparent_25%),linear-gradient(-45deg,#f8fafc_25%,transparent_25%),linear-gradient(45deg,transparent_75%,#f8fafc_75%),linear-gradient(-45deg,transparent_75%,#f8fafc_75%)] bg-[length:16px_16px] bg-[position:0_0,0_8px,8px_-8px,-8px_0px]">
          {unfoldSvgUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={unfoldSvgUrl}
              alt="Unfold preview"
              className="max-h-full max-w-full object-contain p-4"
            />
          ) : (
            <div className="px-6 text-center">
              <FileImage className="mx-auto mb-3 h-10 w-10 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                Generate a template to see the unfold layout here.
              </p>
            </div>
          )}
        </div>

        <ExportPanel disabled={status !== "ready"} />
      </CardContent>
    </Card>
  );
}

function ExportPanel({ disabled }: { disabled: boolean }) {
  return (
    <div className="mt-4 space-y-2">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Download
      </p>
      <div className="grid grid-cols-1 gap-2">
        <Button variant="outline" disabled={disabled} className="justify-start">
          <FileText className="mr-2 h-4 w-4" />
          Export PDF
        </Button>
        <Button variant="outline" disabled={disabled} className="justify-start">
          <Download className="mr-2 h-4 w-4" />
          Export SVG
        </Button>
        <Button variant="outline" disabled={disabled} className="justify-start">
          <Package className="mr-2 h-4 w-4" />
          Export ZIP
        </Button>
      </div>
    </div>
  );
}
