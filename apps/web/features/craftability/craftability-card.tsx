"use client";

import { AlertTriangle, CheckCircle2, Info } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CraftabilityScore } from "@/types";

const LEVEL_CONFIG = {
  excellent: {
    label: "Excellent",
    variant: "success" as const,
    icon: CheckCircle2,
    bar: "bg-emerald-500",
  },
  good: {
    label: "Good",
    variant: "success" as const,
    icon: CheckCircle2,
    bar: "bg-emerald-400",
  },
  fair: {
    label: "Fair",
    variant: "warning" as const,
    icon: Info,
    bar: "bg-amber-400",
  },
  poor: {
    label: "Poor",
    variant: "warning" as const,
    icon: AlertTriangle,
    bar: "bg-orange-500",
  },
};

type CraftabilityCardProps = {
  craftability: CraftabilityScore | null;
  compact?: boolean;
};

export function CraftabilityCard({ craftability, compact = false }: CraftabilityCardProps) {
  if (!craftability) {
    return (
      <Card className="border-border/70 shadow-none">
        <CardContent className={compact ? "py-4" : "py-6"}>
          <p className="text-sm text-muted-foreground">
            Generate a template to see craftability score.
          </p>
        </CardContent>
      </Card>
    );
  }

  const config =
    LEVEL_CONFIG[craftability.level as keyof typeof LEVEL_CONFIG] ?? LEVEL_CONFIG.fair;
  const Icon = config.icon;

  return (
    <Card className="border-border/70 shadow-none">
      <CardHeader className={compact ? "pb-2" : "pb-3"}>
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">Craftability</CardTitle>
          <Badge variant={config.variant}>{config.label}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-end gap-3">
          <span className="text-3xl font-bold tabular-nums text-primary">
            {craftability.score}
          </span>
          <span className="pb-1 text-sm text-muted-foreground">/ 100</span>
          <Icon className="ml-auto h-5 w-5 text-muted-foreground" />
        </div>

        <div className="h-2 overflow-hidden rounded-full bg-muted">
          <div
            className={`h-full rounded-full transition-all ${config.bar}`}
            style={{ width: `${craftability.score}%` }}
          />
        </div>

        {!compact && craftability.warnings.length > 0 && (
          <ul className="space-y-1.5 rounded-xl bg-amber-50 px-3 py-2.5 text-xs text-amber-900">
            {craftability.warnings.map((warning) => (
              <li key={warning} className="flex gap-2">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>{warning}</span>
              </li>
            ))}
          </ul>
        )}

        {compact && craftability.warnings.length > 0 && (
          <p className="text-xs text-muted-foreground">
            {craftability.warnings.length} note
            {craftability.warnings.length > 1 ? "s" : ""} — see log below
          </p>
        )}
      </CardContent>
    </Card>
  );
}
