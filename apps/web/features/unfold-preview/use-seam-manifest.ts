"use client";

import { useEffect, useState } from "react";

import {
  parseSeamManifest,
  seamManifestPreviewUrl,
  type SeamManifest,
} from "@/lib/seam-manifest";

export function useSeamManifest(
  projectId: string | null,
  revision: number,
  enabled: boolean,
): SeamManifest | null {
  const [manifest, setManifest] = useState<SeamManifest | null>(null);

  useEffect(() => {
    if (!enabled || !projectId) {
      setManifest(null);
      return;
    }

    let cancelled = false;
    setManifest(null);

    void fetch(seamManifestPreviewUrl(projectId, revision))
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => {
        if (!cancelled && payload) {
          setManifest(parseSeamManifest(payload));
        }
      })
      .catch(() => {
        /* manifest optional for older exports */
      });

    return () => {
      cancelled = true;
    };
  }, [projectId, revision, enabled]);

  return manifest;
}
