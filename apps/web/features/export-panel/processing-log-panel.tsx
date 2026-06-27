"use client";

import { AlertCircle } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useStudioStore } from "@/store/studio-store";

const STATUS_PROGRESS: Record<string, number> = {
  created: 0,
  uploaded: 25,
  processing: 60,
  ready: 100,
  failed: 100,
};

export function ProcessingLogPanel() {
  const { status, logs, error } = useStudioStore();

  return (
    <Card className="border-border/70 shadow-none">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-4">
          <CardTitle className="text-base">Processing Log</CardTitle>
          <span className="text-xs capitalize text-muted-foreground">{status}</span>
        </div>
        <Progress value={STATUS_PROGRESS[status] ?? 0} className="mt-2" />
      </CardHeader>
      <CardContent className="space-y-3">
        {error && (
          <div className="flex items-start gap-2 rounded-xl bg-destructive/10 px-3 py-2 text-sm text-destructive">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="max-h-32 overflow-y-auto rounded-xl bg-muted/40 p-3 font-mono text-xs text-muted-foreground">
          {logs.length === 0 ? (
            <p>Waiting for activity...</p>
          ) : (
            logs.map((line, index) => <p key={`${line}-${index}`}>{line}</p>)
          )}
        </div>
      </CardContent>
    </Card>
  );
}
