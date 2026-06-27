"use client";

import { useCallback, useRef, useState } from "react";
import { ImageIcon, Loader2, Sparkles, Upload } from "lucide-react";

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
import { generateFromImage } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useStudioStore } from "@/store/studio-store";
import type { Style } from "@/types";

const ACCEPTED_IMAGES = ".jpg,.jpeg,.png,.webp";

export function ImageToModelPanel() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [style, setStyle] = useState<Style>("low_poly");
  const [hint, setHint] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const { setGenerationResult, addLog, setError } = useStudioStore();

  const handleFile = useCallback((file: File | null) => {
    if (!file) return;
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  }, []);

  const handleGenerate = async () => {
    if (!selectedFile) {
      setError("Please choose an image first.");
      return;
    }

    setIsGenerating(true);
    setError(null);
    addLog(`Generating 3D model from image: ${selectedFile.name}`);

    try {
      const data = await generateFromImage({
        file: selectedFile,
        style,
        hint: hint.trim() || undefined,
      });
      setGenerationResult({
        projectId: data.projectId,
        sourceFileUrl: data.sourceFileUrl,
        fileName: selectedFile.name.replace(/\.[^.]+$/, "") + ".glb",
        sourceType: "image_to_3d",
        sourcePrompt: data.sourcePrompt,
        sourceImageUrl: data.sourceImageUrl,
        aiProvider: data.aiProvider,
        enhancedPrompt: data.enhancedPrompt,
      });
      addLog(`AI model ready (${data.aiProvider}). Project: ${data.projectId}`);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Image generation failed.";
      setError(message);
      addLog(`Error: ${message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-4">
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          handleFile(event.dataTransfer.files?.[0] ?? null);
        }}
        className={cn(
          "flex min-h-[140px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-4 py-6 text-center transition-colors",
          isDragging
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50 hover:bg-muted/40",
        )}
      >
        {previewUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={previewUrl}
            alt="Preview"
            className="max-h-28 max-w-full rounded-lg object-contain"
          />
        ) : (
          <>
            <ImageIcon className="mb-2 h-8 w-8 text-primary" />
            <p className="text-sm font-medium">Drop photo or sketch here</p>
            <p className="mt-1 text-xs text-muted-foreground">
              JPG · PNG · WebP · Silhouettes work best
            </p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_IMAGES}
          className="hidden"
          onChange={(event) => handleFile(event.target.files?.[0] ?? null)}
        />
      </div>

      {selectedFile && (
        <Badge variant="secondary" className="truncate">
          {selectedFile.name}
        </Badge>
      )}

      <div className="space-y-2">
        <Label htmlFor="image-hint">Hint (optional)</Label>
        <input
          id="image-hint"
          value={hint}
          onChange={(event) => setHint(event.target.value)}
          placeholder="e.g. Make it a cute papercraft animal"
          className="flex h-10 w-full rounded-xl border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      <div className="space-y-2">
        <Label>Style</Label>
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

      <div className="grid grid-cols-2 gap-2">
        <Button
          variant="outline"
          disabled={isGenerating}
          onClick={() => inputRef.current?.click()}
        >
          <Upload className="mr-1 h-4 w-4" />
          Choose Image
        </Button>
        <Button
          disabled={isGenerating || !selectedFile}
          onClick={() => void handleGenerate()}
        >
          {isGenerating ? (
            <Loader2 className="mr-1 h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="mr-1 h-4 w-4" />
          )}
          Generate
        </Button>
      </div>
    </div>
  );
}
