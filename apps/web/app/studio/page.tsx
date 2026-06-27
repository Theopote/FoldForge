import { ModelPreviewPanel } from "@/features/model-preview/model-preview-panel";
import { ModelUploadPanel } from "@/features/model-upload/model-upload-panel";
import { ProcessingLogPanel } from "@/features/export-panel/processing-log-panel";
import { ProjectSettingsPanel } from "@/features/project-settings/project-settings-panel";
import { UnfoldPreviewPanel } from "@/features/unfold-preview/unfold-preview-panel";
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
        <Badge variant="secondary">MVP · Upload 3D only</Badge>
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left sidebar */}
        <aside className="space-y-6 lg:col-span-3">
          <section className="rounded-2xl border border-border/70 bg-card p-4">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Upload
            </h2>
            <ModelUploadPanel />
          </section>
          <ProjectSettingsPanel />
        </aside>

        {/* Center — 3D preview */}
        <section className="lg:col-span-5">
          <ModelPreviewPanel />
        </section>

        {/* Right — 2D unfold */}
        <section className="lg:col-span-4">
          <UnfoldPreviewPanel />
        </section>
      </div>

      {/* Bottom log */}
      <div className="mt-6">
        <ProcessingLogPanel />
      </div>
    </div>
  );
}
