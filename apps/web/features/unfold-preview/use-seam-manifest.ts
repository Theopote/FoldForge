"use client";

import { useEffect, useState } from "react";

import {
  parseSeamManifest,
  seamManifestPreviewUrl,
  type SeamManifest,
} from "@/lib/seam-manifest";

type ManifestState = {
  key: string;
  manifest: SeamManifest | null;
};

export function useSeamManifest(
  projectId: string | null,
  revision: number,
  enabled: boolean,
): SeamManifest | null {
  const [state, setState] = useState<ManifestState | null>(null);
  const key = enabled && projectId ? `${projectId}:${revision}` : null;

  useEffect(() => {
    if (!key || !projectId) return;

    let cancelled = false;

    void fetch(seamManifestPreviewUrl(projectId, revision))
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => {
        if (!cancelled && payload) {
          setState({ key, manifest: parseSeamManifest(payload) });
        }
      })
      .catch(() => {
        /* manifest optional for older exports */
      });

    return () => {
      cancelled = true;
    };
  }, [projectId, revision, key]);

  return state?.key === key ? state.manifest : null;
}
