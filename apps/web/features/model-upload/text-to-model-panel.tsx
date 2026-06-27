"use client";

import { useState } from "react";
import { Loader2, Sparkles, Wand2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { generateFromText } from "@/lib/api";
import { useStudioStore } from "@/store/studio-store";
import type { Style } from "@/types";

const EXAMPLE_PROMPTS = [
  "A low poly cat for papercraft",
  "Cute chibi robot toy",
  "Geometric castle tower",
  "Simple fantasy tree",
  "Cartoon racing car",
];

export function TextToModelPanel() {
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState<Style>("low_poly");
  const [isGenerating, setIsGenerating] = useState(false);
  const { setGenerationResult, addLog, setError } = useStudioStore();

  const handleGenerate = async () => {
    if (prompt.trim().length < 3) {
      setError("Please enter at least 3 characters.");
      return;
    }

    setIsGenerating(true);
    setError(null);
    addLog(`Generating 3D model from text: "${prompt.slice(0, 60)}..."`);

    try {
      const data = await generateFromText({ prompt: prompt.trim(), style });
      setGenerationResult({
        projectId: data.projectId,
        sourceFileUrl: data.sourceFileUrl,
        fileName: `${data.sourcePrompt?.slice(0, 32) ?? "ai-model"}.glb`,
        sourceType: "text_to_3d",
        sourcePrompt: data.sourcePrompt,
        aiProvider: data.aiProvider,
        enhancedPrompt: data.enhancedPrompt,
      });
      addLog(`AI model ready (${data.aiProvider}). Project: ${data.projectId}`);
      if (data.enhancedPrompt) {
        addLog(`Enhanced prompt applied for papercraft style.`);
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Text generation failed.";
      setError(message);
      addLog(`Error: ${message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-dashed border-primary/30 bg-primary/5 px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-medium text-primary">
          <Wand2 className="h-4 w-4" />
          Describe your papercraft
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          AI generates a low-poly 3D model optimized for printable folding.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="text-prompt">Prompt</Label>
        <textarea
          id="text-prompt"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="e.g. A cute low poly fox for beginners"
          rows={4}
          className="w-full resize-none rounded-xl border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      <div className="space-y-2">
        <Label>Generation Style</Label>
        <Select value={style} onValueChange={(v) => setStyle(v as Style)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="low_poly">Low Poly</SelectItem>
            <SelectItem value="cute">Cute / Chibi</SelectItem>
            <SelectItem value="geometric">Geometric</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label className="text-xs text-muted-foreground">Try an example</Label>
        <div className="flex flex-wrap gap-1.5">
          {EXAMPLE_PROMPTS.map((example) => (
            <Badge
              key={example}
              variant="outline"
              className="cursor-pointer hover:bg-muted"
              onClick={() => setPrompt(example)}
            >
              {example}
            </Badge>
          ))}
        </div>
      </div>

      <Button
        className="w-full"
        disabled={isGenerating || prompt.trim().length < 3}
        onClick={() => void handleGenerate()}
      >
        {isGenerating ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Generating 3D…
          </>
        ) : (
          <>
            <Sparkles className="mr-2 h-4 w-4" />
            Generate 3D Model
          </>
        )}
      </Button>
    </div>
  );
}
