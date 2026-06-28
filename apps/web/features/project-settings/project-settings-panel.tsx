"use client";

import Link from "next/link";
import { useEffect } from "react";
import { Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { cancelProcessJob, processModel } from "@/lib/api";
import { applyTerminalProcessJob } from "@/features/studio/resume-process";
import { beginJobPoll, cancelJobPoll } from "@/lib/job-poll-session";
import {
  clearJobProgressTracking,
  reportJobProgress,
} from "@/lib/job-progress";
import { isAbortError } from "@/lib/poll-utils";
import {
  formatProcessJobError,
  isProcessJobCancelled,
} from "@/lib/process-errors";
import { useStudioStore } from "@/store/studio-store";
import type { CraftabilityScore } from "@/types";

export function ProjectSettingsPanel() {
  const {
    settings,
    updateSettings,
    projectId,
    status,
    beginPapercraftProcessing,
    completePapercraftProcessing,
    addLog,
    setError,
    setActiveProcessJobId,
    activeProcessJobId,
  } = useStudioStore();

  useEffect(() => () => cancelJobPoll("process"), []);

  const handleGenerate = async () => {
    if (!projectId) {
      setError("Please upload or generate a 3D model first.");
      return;
    }

    setError(null);
    beginPapercraftProcessing();
    clearJobProgressTracking();
    reportJobProgress("papercraft_process", 0, "Queued");
    addLog("Starting papercraft generation...");

    const signal = beginJobPoll("process");

    try {
      const data = await processModel(projectId, settings, {
        signal,
        onProgress: (job) => {
          if (signal.aborted) return;
          setActiveProcessJobId(job.jobId);
          reportJobProgress("papercraft_process", job.progress, job.message);
        },
      });

      if (signal.aborted) return;

      setActiveProcessJobId(null);
      clearJobProgressTracking();
      completePapercraftProcessing({
        processedModelUrl: data.processedModelUrl ?? null,
        unfoldSvgUrl: data.unfoldSvgUrl ?? null,
        unfoldPdfUrl: data.unfoldPdfUrl ?? null,
        unfoldZipUrl: data.unfoldZipUrl ?? null,
        stats: data.stats ?? null,
        craftability: (data.craftability as CraftabilityScore | undefined) ?? null,
        status: data.status as typeof status,
      });

      if (data.stats) {
        addLog(
          `Generated ${data.stats.pieces} pieces across ${data.stats.pages} page(s), ${data.stats.faces} faces`,
        );
      }
      if (settings.colorMode === "color") {
        addLog("Surface colors baked into SVG and PDF exports.");
      }
      if (data.craftability) {
        addLog(
          `Craftability: ${data.craftability.score}/100 (${data.craftability.level})`,
        );
        for (const warning of data.craftability.warnings) {
          addLog(`Note: ${warning}`);
        }
      }
    } catch (error) {
      if (isAbortError(error) || isProcessJobCancelled(error)) return;

      const message = formatProcessJobError(error, "Generation failed.");
      setError(message);
      useStudioStore.getState().setStatus("failed");
      setActiveProcessJobId(null);
      clearJobProgressTracking();
      addLog(`Error: ${message}`);
    }
  };

  const handleCancel = async () => {
    if (!activeProcessJobId) return;

    cancelJobPoll("process");
    try {
      const job = await cancelProcessJob(activeProcessJobId);
      if (applyTerminalProcessJob(job)) {
        return;
      }

      setActiveProcessJobId(null);
      clearJobProgressTracking();
      useStudioStore.getState().setStatus("uploaded");
      addLog("Processing cancelled.");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to cancel processing.";
      addLog(`Error: ${message}`);
    }
  };

  return (
    <Card className="border-border/70 shadow-none">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="h-4 w-4 text-primary" />
          Project Settings
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-2">
          <Label>Paper Size</Label>
          <Select
            value={settings.paperSize}
            onValueChange={(value) =>
              updateSettings({
                paperSize: value as typeof settings.paperSize,
              })
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="A4">A4 (210 × 297 mm)</SelectItem>
              <SelectItem value="A3">A3 (297 × 420 mm)</SelectItem>
              <SelectItem value="Letter">Letter (8.5 × 11 in)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>Difficulty</Label>
          <Select
            value={settings.difficulty}
            onValueChange={(value) =>
              updateSettings({
                difficulty: value as typeof settings.difficulty,
              })
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="easy">Easy — fewer pieces, beginner friendly</SelectItem>
              <SelectItem value="standard">Standard — balanced detail</SelectItem>
              <SelectItem value="advanced">Advanced — more detail & pieces</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>Style</Label>
          <Select
            value={settings.style}
            onValueChange={(value) =>
              updateSettings({ style: value as typeof settings.style })
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="low_poly">Low Poly</SelectItem>
              <SelectItem value="cute">Cute / Chibi</SelectItem>
              <SelectItem value="geometric">Geometric Sculpture</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="target-height">Target Height (mm)</Label>
          <input
            id="target-height"
            type="number"
            min={50}
            max={500}
            value={settings.targetHeightMm}
            onChange={(event) =>
              updateSettings({ targetHeightMm: Number(event.target.value) })
            }
            className="flex h-10 w-full rounded-xl border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="space-y-3 rounded-xl bg-muted/40 p-3">
          {(
            [
              ["addTabs", "Glue tabs"],
              ["addNumbers", "Part numbers"],
              ["addFoldLines", "Fold lines"],
              ["addCutLines", "Cut lines"],
            ] as const
          ).map(([key, label]) => (
            <div key={key} className="flex items-center justify-between">
              <Label htmlFor={key}>{label}</Label>
              <Switch
                id={key}
                checked={settings[key]}
                onCheckedChange={(checked) => updateSettings({ [key]: checked })}
              />
            </div>
          ))}
        </div>

        <div className="space-y-2">
          <Label>Color Mode</Label>
          <div className="flex gap-2">
            <Badge
              variant={settings.colorMode === "line_art" ? "default" : "outline"}
              className="cursor-pointer"
              onClick={() => updateSettings({ colorMode: "line_art" })}
            >
              Line Art
            </Badge>
            <Badge
              variant={settings.colorMode === "color" ? "default" : "outline"}
              className="cursor-pointer"
              onClick={() => updateSettings({ colorMode: "color" })}
            >
              Color
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Color mode bakes mesh surface colors into the unfold preview and exports.
          </p>
        </div>

        <Button
          className="w-full"
          size="lg"
          disabled={!projectId || status === "processing"}
          onClick={() => void handleGenerate()}
        >
          {status === "processing" ? "Generating template…" : "Generate Template"}
        </Button>

        {status === "processing" && activeProcessJobId && (
          <Button
            variant="outline"
            className="w-full"
            onClick={() => void handleCancel()}
          >
            Cancel processing
          </Button>
        )}

        {status === "ready" && projectId && (
          <Button variant="outline" className="w-full" asChild>
            <Link href={`/projects/${projectId}`}>View Project Details</Link>
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
