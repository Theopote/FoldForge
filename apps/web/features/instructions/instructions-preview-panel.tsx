"use client";

import { useEffect, useState } from "react";
import { BookOpen, Download, FileText, Layers } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  assemblyStepsPreviewUrl,
  instructionExportUrls,
  instructionPreviewUrl,
} from "@/lib/instruction-urls";
import { useStudioStore } from "@/store/studio-store";

type PreviewTab = "text" | "steps";

const STEPS_SVG_STYLES = `
.assembly-steps-host svg {
  display: block;
  height: auto;
  max-height: 100%;
  max-width: 100%;
  width: auto;
}
`;

export function InstructionsPreviewPanel() {
  const { projectId, status, exportRevision } = useStudioStore();
  const [tab, setTab] = useState<PreviewTab>("text");
  const [text, setText] = useState<string | null>(null);
  const [stepsSvg, setStepsSvg] = useState<string | null>(null);
  const [error, setError] = useState(false);

  const isReady = status === "ready" && projectId !== null;

  useEffect(() => {
    if (!isReady || !projectId) {
      setText(null);
      setStepsSvg(null);
      setError(false);
      return;
    }

    let cancelled = false;
    setText(null);
    setStepsSvg(null);
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

    void fetch(assemblyStepsPreviewUrl(projectId, exportRevision))
      .then((response) => {
        if (!response.ok) {
          return null;
        }
        return response.text();
      })
      .then((content) => {
        if (!cancelled && content) {
          setStepsSvg(content);
        }
      })
      .catch(() => {
        /* steps SVG is optional for older exports */
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
          <div className="flex flex-wrap gap-2">
            <Button
              variant={tab === "text" ? "secondary" : "outline"}
              size="sm"
              onClick={() => setTab("text")}
            >
              <FileText className="mr-1.5 h-3.5 w-3.5" />
              Text
            </Button>
            <Button
              variant={tab === "steps" ? "secondary" : "outline"}
              size="sm"
              onClick={() => setTab("steps")}
              disabled={!stepsSvg}
            >
              <Layers className="mr-1.5 h-3.5 w-3.5" />
              Steps
            </Button>
            <Button variant="outline" size="sm" asChild>
              <a href={urls.txtAuth} download={`${projectId}-instructions.txt`}>
                TXT
              </a>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <a href={urls.pdfAuth} download={`${projectId}-instructions.pdf`}>
                PDF
              </a>
            </Button>
            {stepsSvg && (
              <Button variant="outline" size="sm" asChild>
                <a href={urls.stepsSvgAuth} download={`${projectId}-assembly-steps.svg`}>
                  <Download className="mr-1.5 h-3.5 w-3.5" />
                  SVG
                </a>
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <p className="text-sm text-destructive">
            Could not load assembly guide. Download the ZIP kit or retry after regeneration.
          </p>
        )}
        {!error && tab === "text" && !text && (
          <p className="text-sm text-muted-foreground">Loading assembly guide…</p>
        )}
        {!error && tab === "text" && text && (
          <pre className="max-h-80 overflow-auto rounded-xl border border-border bg-muted/30 p-4 text-xs leading-relaxed whitespace-pre-wrap">
            {text}
          </pre>
        )}
        {!error && tab === "steps" && !stepsSvg && (
          <p className="text-sm text-muted-foreground">
            Step illustrations are not available yet. Regenerate the template to create
            assembly-steps.svg.
          </p>
        )}
        {!error && tab === "steps" && stepsSvg && (
          <>
            <style>{STEPS_SVG_STYLES}</style>
            <div
              className="assembly-steps-host max-h-96 overflow-auto rounded-xl border border-border bg-muted/20 p-4"
              dangerouslySetInnerHTML={{ __html: stepsSvg }}
            />
          </>
        )}
      </CardContent>
    </Card>
  );
}
