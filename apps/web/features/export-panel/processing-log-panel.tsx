"use client";

import { AlertCircle, AlertTriangle } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useStudioStore } from "@/store/studio-store";

const STATUS_PROGRESS: Record<string, number> = {
  created: 0,
  uploaded: 25,
  processing: 10,
  ready: 100,
  failed: 100,
};

const JOB_PHASE_LABEL: Record<string, string> = {
  ai_generation: "AI generation",
  papercraft_process: "Papercraft pipeline",
};

export function ProcessingLogPanel() {
  const {
    status,
    logs,
    error,
    craftability,
    jobPhase,
    jobProgress,
    jobMessage,
  } = useStudioStore();

  const isJobActive = jobPhase !== "idle";
  const progressValue = isJobActive ? jobProgress : (STATUS_PROGRESS[status] ?? 0);
  const statusLabel = isJobActive
    ? `${JOB_PHASE_LABEL[jobPhase] ?? "Working"} · ${jobProgress}%`
    : status;

  return (
    <Card className="border-border/70 shadow-none">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-4">
          <CardTitle className="text-base">Processing Log</CardTitle>
          <span className="text-xs capitalize text-muted-foreground">
            {statusLabel}
          </span>
        </div>
        <Progress value={progressValue} className="mt-2" />
        {isJobActive && jobMessage && (
          <p className="mt-2 text-xs text-muted-foreground">{jobMessage}</p>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {error && (
          <div className="flex items-start gap-2 rounded-xl bg-destructive/10 px-3 py-2 text-sm text-destructive">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {craftability && craftability.warnings.length > 0 && (
          <div className="rounded-xl bg-amber-50 px-3 py-2.5">
            <p className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-amber-900">
              <AlertTriangle className="h-3.5 w-3.5" />
              Craftability notes
            </p>
            <ul className="space-y-1 text-xs text-amber-800">
              {craftability.warnings.map((warning) => (
                <li key={warning}>• {warning}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="max-h-40 overflow-y-auto rounded-xl bg-muted/40 p-3 font-mono text-xs text-muted-foreground">
          {logs.length === 0 ? (
            <p>Waiting for activity…</p>
          ) : (
            logs.map((line, index) => <p key={`${line}-${index}`}>{line}</p>)
          )}
        </div>
      </CardContent>
    </Card>
  );
}
