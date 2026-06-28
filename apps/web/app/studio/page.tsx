import { Suspense } from "react";

import { StudioWorkspace } from "@/features/studio/studio-workspace";
import { Badge } from "@/components/ui/badge";

export default function StudioPage() {
  return (
    <div className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Studio</h1>
          <p className="text-sm text-muted-foreground">
            Upload a 3D model, tune settings, and generate a printable papercraft
            template.
          </p>
        </div>
        <Badge variant="secondary">Phase 2 · AI Input</Badge>
      </div>

      <Suspense fallback={null}>
        <StudioWorkspace />
      </Suspense>
    </div>
  );
}
