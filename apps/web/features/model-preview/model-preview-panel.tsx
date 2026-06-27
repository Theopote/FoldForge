"use client";

import { Box, Rotate3D } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useStudioStore } from "@/store/studio-store";

export function ModelPreviewPanel() {
  const { sourceFileUrl, status, stats } = useStudioStore();

  return (
    <Card className="flex h-full min-h-[420px] flex-col border-border/70 shadow-none">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Box className="h-4 w-4 text-primary" />
          3D Preview
        </CardTitle>
        <Badge variant="secondary">{status}</Badge>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col">
        <div className="relative flex flex-1 flex-col items-center justify-center overflow-hidden rounded-2xl border border-dashed border-border bg-gradient-to-br from-sky-50 via-white to-orange-50">
          <Rotate3D className="mb-4 h-12 w-12 text-primary/40" />
          <p className="text-sm font-medium text-foreground/80">
            {sourceFileUrl
              ? "3D viewer will load here (Step 4)"
              : "Upload a model to preview"}
          </p>
          <p className="mt-1 max-w-xs text-center text-xs text-muted-foreground">
            Orbit controls, face count, and craftability score coming next.
          </p>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-3 text-center">
          <Metric label="Faces" value={stats?.faces ?? "—"} />
          <Metric label="Pieces" value={stats?.pieces ?? "—"} />
          <Metric label="Pages" value={stats?.pages ?? "—"} />
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl bg-muted/40 px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-semibold">{value}</p>
    </div>
  );
}
