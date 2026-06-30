"use client";

import { useEffect, useMemo, useState } from "react";
import { Cpu, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { getAiProviders, type AiProviderInfo } from "@/lib/api";

type AiMode = "text" | "image";

export function AiProviderStatus({ mode }: { mode: AiMode }) {
  const [providers, setProviders] = useState<AiProviderInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getAiProviders()
      .then((items) => {
        if (!cancelled) {
          setProviders(items);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "AI status unavailable.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const active = useMemo(
    () => providers?.find((provider) => provider.active && provider.name !== "auto"),
    [providers],
  );

  if (error) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
        AI provider status unavailable. Start the API server to enable real AI generation.
      </div>
    );
  }

  if (!providers || !active) {
    return (
      <div className="flex items-center gap-2 rounded-xl border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Checking AI provider...
      </div>
    );
  }

  const supportsMode = mode === "text" ? active.text : active.image;
  const realProvider = active.name !== "mock";
  const ready = active.available && supportsMode && realProvider;
  const message = ready
    ? `${active.name} is active for ${mode}-to-3D.`
    : active.name === "mock"
      ? "Offline procedural mode is active. Configure Meshy or Replicate for real AI generation."
      : active.reason || `${active.name} is not configured for ${mode}-to-3D.`;

  return (
    <div className="flex items-start gap-2 rounded-xl border bg-muted/30 px-3 py-2 text-xs">
      <Cpu className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-foreground">AI backend</span>
          <Badge variant={ready ? "default" : "outline"} className="h-5 px-1.5 text-[10px]">
            {active.name}
          </Badge>
          {active.async && (
            <Badge variant="secondary" className="h-5 px-1.5 text-[10px]">
              async
            </Badge>
          )}
        </div>
        <p className="mt-1 text-muted-foreground">{message}</p>
      </div>
    </div>
  );
}
