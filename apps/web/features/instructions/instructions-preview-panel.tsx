"use client";

import { useEffect, useState } from "react";
import { BookOpen, Download, FileText } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { instructionExportUrls, instructionPreviewUrl } from "@/lib/instruction-urls";
import { useStudioStore } from "@/store/studio-store";

export function InstructionsPreviewPanel() {
  const { projectId, status, exportRevision } = useStudioStore();
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState(false);

  const isReady = status === "ready" && projectId !== null;

  useEffect(() => {
    if (!isReady || !projectId) {
      setText(null);
      setError(false);
      return;
    }

    let cancelled = false;
    setText(null);
    setError(false);

    void fetch(instructionPreviewUrl(projectId, exportRevision))
      .then((response) => {
        if (!response.ok) {
          throw new Error("instructions fetch failed");
        }
        return response.text();
      })
      .then((content) => {
        if (!cancelled) {
          setText(content);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError(true);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [isReady, projectId, exportRevision]);

  if (!isReady || !projectId) {
    return null;
  }

  const urls = instructionExportUrls(projectId);

  return (
    <Card className="border-border/70 shadow-none">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <BookOpen className="h-4 w-4" />
            Assembly Guide
          </CardTitle>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" asChild>
              <a href={urls.txtAuth} download={`${projectId}-instructions.txt`}>
                <FileText className="mr-1.5 h-3.5 w-3.5" />
                TXT
              </a>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <a href={urls.pdfAuth} download={`${projectId}-instructions.pdf`}>
                <Download className="mr-1.5 h-3.5 w-3.5" />
                PDF
              </a>
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <p className="text-sm text-destructive">
            Could not load assembly guide. Download the ZIP kit or retry after regeneration.
          </p>
        )}
        {!error && !text && (
          <p className="text-sm text-muted-foreground">Loading assembly guide…</p>
        )}
        {text && (
          <pre className="max-h-80 overflow-auto rounded-xl border border-border bg-muted/30 p-4 text-xs leading-relaxed whitespace-pre-wrap">
            {text}
          </pre>
        )}
      </CardContent>
    </Card>
  );
}
