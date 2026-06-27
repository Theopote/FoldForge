"use client";

import { useCallback, useRef, useState } from "react";
import { FileUp, Loader2, Sparkles, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { uploadModel } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useStudioStore } from "@/store/studio-store";

const ACCEPTED_TYPES = ".obj,.stl,.glb,.gltf";

export function ModelUploadPanel() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const {
    projectId,
    sourceFileName,
    sourceFileUrl,
    setUploadResult,
    addLog,
    setError,
  } = useStudioStore();

  const uploadFile = useCallback(
    async (file: File) => {
      setIsUploading(true);
      setError(null);
      addLog(`Uploading ${file.name}...`);

      try {
        const data = await uploadModel(file);
        setUploadResult({
          projectId: data.projectId,
          sourceFileUrl: data.sourceFileUrl,
          fileName: file.name,
        });
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
    [addLog, setError, setUploadResult],
  );

  const handleFiles = useCallback(
    (files: FileList | null) => {
      const file = files?.[0];
      if (!file) return;
      void uploadFile(file);
    },
    [uploadFile],
  );

  const loadSample = useCallback(async () => {
    setIsUploading(true);
    setError(null);
    addLog("Loading sample model (box.stl)...");

    try {
      const response = await fetch("/samples/box.stl");
      if (!response.ok) throw new Error("Failed to load sample model.");

      const blob = await response.blob();
      const file = new File([blob], "box.stl", { type: "model/stl" });
      await uploadFile(file);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Sample load failed.";
      setError(message);
      addLog(`Error: ${message}`);
      setIsUploading(false);
    }
  }, [addLog, setError, uploadFile]);

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
          handleFiles(event.dataTransfer.files);
        }}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-4 py-8 text-center transition-colors",
          isDragging
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50 hover:bg-muted/40",
          isUploading && "pointer-events-none opacity-70",
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
          onChange={(event) => handleFiles(event.target.files)}
        />
      </div>

      {sourceFileUrl && (
        <div className="space-y-1 rounded-xl bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <FileUp className="h-4 w-4 shrink-0 text-primary" />
            <span className="truncate font-medium text-foreground">
              {sourceFileName}
            </span>
          </div>
          {projectId && (
            <p className="truncate pl-6 font-mono text-[10px]">ID: {projectId}</p>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        <Button
          variant="outline"
          disabled={isUploading}
          onClick={() => inputRef.current?.click()}
        >
          Choose File
        </Button>
        <Button
          variant="outline"
          disabled={isUploading}
          onClick={() => void loadSample()}
        >
          <Sparkles className="mr-1 h-4 w-4" />
          Try Sample
        </Button>
      </div>
    </div>
  );
}
