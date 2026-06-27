"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Download, FileText, Loader2 } from "lucide-react";

import { CraftabilityCard } from "@/features/craftability/craftability-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CraftabilityScore } from "@/types";

type ProjectDetail = {
  id: string;
  name: string;
  status: string;
  sourceFileUrl?: string;
  processedModelUrl?: string;
  unfoldSvgUrl?: string;
  unfoldPdfUrl?: string;
  unfoldZipUrl?: string;
  craftability?: CraftabilityScore;
  createdAt: string;
  updatedAt: string;
};

export default function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void params.then((p) => setProjectId(p.id));
  }, [params]);

  useEffect(() => {
    if (!projectId) return;

    setLoading(true);
    fetch(`/api/projects/${projectId}`)
      .then(async (response) => {
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error(body.detail ?? "Project not found.");
        }
        return response.json() as Promise<ProjectDetail>;
      })
      .then((data) => {
        setProject(data);
        setError(null);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="mx-auto max-w-lg px-4 py-20 text-center">
        <p className="text-destructive">{error ?? "Project not found."}</p>
        <Button asChild className="mt-4" variant="outline">
          <Link href="/studio">Back to Studio</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <Button asChild variant="ghost" size="sm" className="mb-4">
        <Link href="/studio">
          <ArrowLeft className="mr-1 h-4 w-4" />
          Studio
        </Link>
      </Button>

      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{project.name}</h1>
          <p className="mt-1 font-mono text-xs text-muted-foreground">{project.id}</p>
        </div>
        <Badge variant="secondary" className="capitalize">
          {project.status}
        </Badge>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="border-border/70 shadow-none">
          <CardHeader>
            <CardTitle className="text-base">Downloads</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {project.unfoldPdfUrl && (
              <Button variant="outline" className="w-full justify-start" asChild>
                <a href={project.unfoldPdfUrl} download>
                  <FileText className="mr-2 h-4 w-4" />
                  PDF Template
                </a>
              </Button>
            )}
            {project.unfoldSvgUrl && (
              <Button variant="outline" className="w-full justify-start" asChild>
                <a href={project.unfoldSvgUrl} download>
                  <Download className="mr-2 h-4 w-4" />
                  SVG Template
                </a>
              </Button>
            )}
            {project.unfoldZipUrl && (
              <Button className="w-full justify-start" asChild>
                <a href={project.unfoldZipUrl} download>
                  <Download className="mr-2 h-4 w-4" />
                  Full Kit (ZIP)
                </a>
              </Button>
            )}
            {project.status !== "ready" && (
              <p className="text-sm text-muted-foreground">
                Generate the template in Studio to unlock downloads.
              </p>
            )}
          </CardContent>
        </Card>

        <CraftabilityCard craftability={project.craftability ?? null} />
      </div>

      {project.unfoldSvgUrl && (
        <Card className="mt-6 border-border/70 shadow-none">
          <CardHeader>
            <CardTitle className="text-base">Unfold Preview</CardTitle>
          </CardHeader>
          <CardContent>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={project.unfoldSvgUrl}
              alt="Unfold"
              className="mx-auto max-h-[480px] w-full object-contain"
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
