"use client";

import { useEffect, useState } from "react";

import { unfoldPreviewUrl } from "@/lib/unfold-preview-url";

export type UnfoldPreviewLayer = "both" | "color" | "lines";

const PREVIEW_LAYER_STYLES = `
.unfold-preview-color-only .layer-lines {
  display: none;
}
.unfold-preview-lines-only .layer-baked {
  display: none;
}
.unfold-svg-host svg {
  display: block;
  height: auto;
  max-height: 100%;
  max-width: 100%;
  width: auto;
}
`;

export function UnfoldSvgPreview({
  url,
  revision,
  layer,
  className = "",
}: {
  url: string;
  revision: number;
  layer: UnfoldPreviewLayer;
  className?: string;
}) {
  const [markup, setMarkup] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setMarkup(null);
    setError(false);

    void fetch(unfoldPreviewUrl(url, revision))
      .then((response) => {
        if (!response.ok) {
          throw new Error("preview fetch failed");
        }
        return response.text();
      })
      .then((text) => {
        if (!cancelled) {
          setMarkup(text);
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
  }, [url, revision]);

  const layerClass =
    layer === "color"
      ? "unfold-preview-color-only"
      : layer === "lines"
        ? "unfold-preview-lines-only"
        : "unfold-preview-both";

  if (error) {
    return (
      <p className="px-6 text-center text-sm text-destructive">
        Failed to load unfold preview.
      </p>
    );
  }

  if (!markup) {
    return null;
  }

  return (
    <>
      <style>{PREVIEW_LAYER_STYLES}</style>
      <div
        className={`unfold-svg-host flex h-full w-full items-center justify-center ${layerClass} ${className}`}
        dangerouslySetInnerHTML={{ __html: markup }}
      />
    </>
  );
}
