"use client";

import { useCallback, useRef, useState } from "react";
import { FileUp, Loader2, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useStudioStore } from "@/store/studio-store";

const ACCEPTED_TYPES = ".obj,.stl,.glb,.gltf";

export function ModelUploadPanel() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const { sourceFileUrl, setProjectId, setSourceFileUrl, addLog, setError } =
    useStudioStore();

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      const file = files?.[0];
      if (!file) return;

      setIsUploading(true);
      setError(null);
      addLog(`Uploading ${file.name}...`);

      try {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch("/api/upload-model", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error(body.detail ?? "Upload failed.");
        }

        const data = await response.json();
        setProjectId(data.projectId);
        setSourceFileUrl(data.sourceFileUrl);
        addLog(`Upload complete. Project ID: ${data.projectId}`);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Upload failed.";
        setError(message);
        addLog(`Error: ${message}`);
      } finally {
        setIsUploading(false);
      }
    },
    [addLog, setError, setProjectId, setSourceFileUrl],
  );

  return (
    <div className="space-y-3">
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            inputRef.current?.click();
          }
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          void handleFiles(event.dataTransfer.files);
        }}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-4 py-8 text-center transition-colors",
          isDragging
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50 hover:bg-muted/40",
        )}
      >
        {isUploading ? (
          <Loader2 className="mb-3 h-8 w-8 animate-spin text-primary" />
        ) : (
          <Upload className="mb-3 h-8 w-8 text-primary" />
        )}
        <p className="text-sm font-medium">
          Drop OBJ / STL / GLB here, or click to browse
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Max 50 MB · Triangulated meshes work best
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_TYPES}
          className="hidden"
          onChange={(event) => void handleFiles(event.target.files)}
        />
      </div>

      {sourceFileUrl && (
        <div className="flex items-center gap-2 rounded-xl bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
          <FileUp className="h-4 w-4 shrink-0" />
          <span className="truncate">Model uploaded and ready to generate</span>
        </div>
      )}

      <Button
        variant="outline"
        className="w-full"
        disabled={isUploading}
        onClick={() => inputRef.current?.click()}
      >
        Choose File
      </Button>
    </div>
  );
}
