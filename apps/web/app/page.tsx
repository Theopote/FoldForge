import Link from "next/link";
import {
  ArrowRight,
  Box,
  Layers,
  Printer,
  Scissors,
  Sparkles,
  Upload,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { SAMPLE_CASES } from "@/lib/sample-cases";

const STEPS = [
  {
    icon: Upload,
    title: "Upload or describe",
    description: "Upload a 3D file, describe an idea in text, or start from a photo or sketch.",
  },
  {
    icon: Sparkles,
    title: "Generate printable template",
    description:
      "FoldForge cleans, simplifies, unfolds, and lays out your papercraft kit.",
  },
  {
    icon: Scissors,
    title: "Cut, fold and build",
    description: "Print, cut along the lines, fold, glue tabs, and assemble.",
  },
];

export default function HomePage() {
  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-border/60">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(232,93,76,0.12),transparent_45%),radial-gradient(circle_at_bottom_left,rgba(14,165,233,0.1),transparent_40%)]" />
        <div className="relative mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8 lg:py-28">
          <div className="mx-auto max-w-3xl text-center">
            <Badge variant="secondary" className="mb-4">
              AI Paper Model Studio
            </Badge>
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
              Turn imagination into{" "}
              <span className="text-primary">printable paper models</span>
            </h1>
            <p className="mt-4 text-lg text-muted-foreground sm:text-xl">
              Upload a 3D model, describe an idea, or start from a photo — then
              turn it into a printable papercraft kit with cut lines, fold lines,
              glue tabs, and part numbers.
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              把想象折成立体 · FoldForge / 纸模工坊
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Button asChild size="lg">
                <Link href="/studio">
                  Start Creating
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link href="#how-it-works">See how it works</Link>
              </Button>
            </div>
          </div>

          <div className="mx-auto mt-16 grid max-w-4xl gap-4 sm:grid-cols-3">
            <HeroStat icon={Box} label="3D Upload" value="OBJ · STL · GLB · GLTF" />
            <HeroStat icon={Layers} label="Smart Unfold" value="Tabs & Numbers" />
            <HeroStat icon={Printer} label="Print Ready" value="PDF · SVG · ZIP" />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight">Three steps to your kit</h2>
          <p className="mt-3 text-muted-foreground">
            Designed for hobbyists, parents, and makers — not just 3D professionals.
          </p>
        </div>
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {STEPS.map((step, index) => (
            <Card key={step.title} className="border-border/70 shadow-none">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <step.icon className="h-5 w-5" />
                </div>
                <CardTitle className="text-lg">
                  {index + 1}. {step.title}
                </CardTitle>
                <CardDescription>{step.description}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      </section>

      {/* Examples */}
      <section
        id="examples"
        className="border-t border-border/60 bg-muted/20 py-20"
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-3xl font-bold tracking-tight">Example kits</h2>
              <p className="mt-2 text-muted-foreground">
                Practical starter cases you can preview, generate, and turn into printable kits.
              </p>
            </div>
            <Button asChild variant="outline">
              <Link href="/studio">Try in Studio</Link>
            </Button>
          </div>

          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {SAMPLE_CASES.map((example) => (
              <Card
                key={example.title}
                className="overflow-hidden border-border/70 shadow-none transition hover:shadow-md"
              >
                <div
                  className={`flex min-h-36 flex-col justify-between bg-gradient-to-br ${example.color} p-4`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <Badge variant="outline" className="bg-white/80">
                      {example.tag}
                    </Badge>
                    <Badge variant="secondary">{example.difficulty}</Badge>
                  </div>
                  <div>
                    <p className="text-lg font-semibold">{example.title}</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {example.summary}
                    </p>
                  </div>
                </div>
                <CardContent className="space-y-3 p-4">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Best for
                    </p>
                    <p className="mt-1 text-sm">{example.bestFor}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Suggested setup
                    </p>
                    <p className="mt-1 text-sm">{example.settings}</p>
                  </div>
                  <Button asChild variant="outline" size="sm" className="w-full">
                    <Link
                      href={
                        example.samplePath
                          ? `/studio?sample=${example.id}`
                          : `/studio?promptCase=${example.id}`
                      }
                    >
                      Open in Studio
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
        <Card className="overflow-hidden border-none bg-primary text-primary-foreground">
          <CardContent className="flex flex-col items-start gap-6 p-8 sm:flex-row sm:items-center sm:justify-between sm:p-10">
            <div>
              <h2 className="text-2xl font-bold">Ready to fold something new?</h2>
              <p className="mt-2 text-primary-foreground/90">
                Open the Studio, upload a model, and generate your first template.
              </p>
            </div>
            <Button asChild size="lg" variant="secondary">
              <Link href="/studio">
                Open Studio
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function HeroStat({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-border/70 bg-card/80 px-4 py-4 text-center backdrop-blur-sm">
      <Icon className="mx-auto mb-2 h-5 w-5 text-primary" />
      <p className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}
