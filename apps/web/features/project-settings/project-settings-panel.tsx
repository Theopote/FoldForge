"use client";

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
import { processModel } from "@/lib/api";
import { useStudioStore } from "@/store/studio-store";

export function ProjectSettingsPanel() {
  const {
    settings,
    updateSettings,
    projectId,
    status,
    setStatus,
    setResults,
    addLog,
    setError,
  } = useStudioStore();

  const handleGenerate = async () => {
    if (!projectId) {
      setError("Please upload a 3D model first.");
      return;
    }

    setError(null);
    setStatus("processing");
    addLog("Starting papercraft generation...");

    try {
      const data = await processModel(projectId, settings);

      setResults({
        processedModelUrl: data.processedModelUrl,
        unfoldSvgUrl: data.unfoldSvgUrl,
        unfoldPdfUrl: data.unfoldPdfUrl,
        stats: data.stats,
        craftability: data.craftability,
      });
      setStatus(data.status as typeof status);

      if (data.stats) {
        addLog(
          `Generated ${data.stats.pieces} pieces across ${data.stats.pages} page(s), ${data.stats.faces} faces`,
        );
      }
      if (data.craftability) {
        addLog(
          `Craftability: ${data.craftability.score}/100 (${data.craftability.level})`,
        );
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Generation failed.";
      setError(message);
      setStatus("failed");
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
        </div>

        <Button
          className="w-full"
          size="lg"
          disabled={!projectId || status === "processing"}
          onClick={() => void handleGenerate()}
        >
          {status === "processing" ? "Generating..." : "Generate Template"}
        </Button>
      </CardContent>
    </Card>
  );
}
