import { withStorageAuth } from "@/lib/api-auth";

export type SeamEdgeKind = "cut" | "fold";

export type SeamEdgeInfo = {
  kind: SeamEdgeKind;
  pieceId: string;
  pieceLabel: string;
  lineId: string;
  foldType?: "mountain" | "valley";
  dihedralDeg: number;
  signedDihedralDeg: number;
  hiddenCrease: boolean;
};

export type SeamManifest = {
  version: number;
  edgeCount: number;
  edges: Record<string, SeamEdgeInfo>;
};

export function seamManifestUrls(projectId: string) {
  const json = `/storage/exports/${projectId}.seams.json`;
  return {
    json,
    jsonAuth: withStorageAuth(json),
  };
}

export function seamManifestPreviewUrl(projectId: string, revision: number): string {
  const { jsonAuth } = seamManifestUrls(projectId);
  const separator = jsonAuth.includes("?") ? "&" : "?";
  return `${jsonAuth}${separator}v=${revision}`;
}

export function parseSeamManifest(raw: unknown): SeamManifest | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const payload = raw as Record<string, unknown>;
  const edgesRaw = payload.edges;
  if (!edgesRaw || typeof edgesRaw !== "object") {
    return null;
  }

  const edges: Record<string, SeamEdgeInfo> = {};
  for (const [key, value] of Object.entries(edgesRaw as Record<string, unknown>)) {
    if (!value || typeof value !== "object") {
      continue;
    }
    const edge = value as Record<string, unknown>;
    if (edge.kind !== "cut" && edge.kind !== "fold") {
      continue;
    }
    edges[key] = {
      kind: edge.kind,
      pieceId: String(edge.pieceId ?? ""),
      pieceLabel: String(edge.pieceLabel ?? ""),
      lineId: String(edge.lineId ?? ""),
      foldType:
        edge.foldType === "mountain" || edge.foldType === "valley"
          ? edge.foldType
          : undefined,
      dihedralDeg: Number(edge.dihedralDeg ?? 0),
      signedDihedralDeg: Number(edge.signedDihedralDeg ?? 0),
      hiddenCrease: Boolean(edge.hiddenCrease),
    };
  }

  return {
    version: Number(payload.version ?? 0),
    edgeCount: Number(payload.edgeCount ?? Object.keys(edges).length),
    edges,
  };
}

export function normalizeMeshEdgeKey(raw: string | null | undefined): string | null {
  if (!raw) {
    return null;
  }
  const parts = raw.split(",").map((part) => Number.parseInt(part.trim(), 10));
  if (parts.length !== 2 || parts.some((part) => Number.isNaN(part))) {
    return null;
  }
  const [a, b] = parts;
  return a <= b ? `${a},${b}` : `${b},${a}`;
}

export function parseSeamLineTitle(title: string | null | undefined): {
  edgeKind: string;
  pieceId: string;
  pieceLabel: string;
  meshEdge: string | null;
  lineId: string;
  foldType: string | null;
} | null {
  if (!title) {
    return null;
  }
  const [edgeKind, pieceId, pieceLabel, meshEdge, lineId, foldType] = title.split("|");
  if (!edgeKind || !pieceLabel) {
    return null;
  }
  return {
    edgeKind,
    pieceId: pieceId ?? "",
    pieceLabel,
    meshEdge: normalizeMeshEdgeKey(meshEdge),
    lineId: lineId ?? "",
    foldType: foldType || null,
  };
}

export function readSeamLineMetadata(line: Element): {
  edgeKind: string;
  pieceId: string;
  pieceLabel: string;
  meshEdge: string | null;
  lineId: string;
  foldType: string | null;
} {
  const titleNode = line.querySelector("title");
  const fromTitle = parseSeamLineTitle(titleNode?.textContent);
  if (fromTitle) {
    return fromTitle;
  }
  return {
    edgeKind: line.getAttribute("data-edge-kind") ?? "cut",
    pieceId: line.getAttribute("data-piece-id") ?? "",
    pieceLabel: line.getAttribute("data-piece-label") ?? "",
    meshEdge: normalizeMeshEdgeKey(line.getAttribute("data-mesh-edge")),
    lineId: line.getAttribute("data-line-id") ?? line.id ?? "",
    foldType: line.getAttribute("data-fold-type"),
  };
}

export function formatSeamTooltip(
  meshEdge: string,
  attrs: {
    pieceLabel?: string | null;
    edgeKind?: string | null;
    foldType?: string | null;
  },
  manifestEdge?: SeamEdgeInfo,
): string {
  const kind = attrs.edgeKind === "fold" ? "Fold" : "Cut seam";
  const piece = attrs.pieceLabel ? `Piece ${attrs.pieceLabel}` : "Piece";
  const lines = [`${kind} · ${piece}`, `Mesh edge ${meshEdge}`];

  if (manifestEdge) {
    lines.push(`Dihedral ${manifestEdge.dihedralDeg.toFixed(1)}°`);
    if (manifestEdge.kind === "fold" && manifestEdge.foldType) {
      lines.push(`${manifestEdge.foldType} fold`);
    }
    if (manifestEdge.hiddenCrease) {
      lines.push("Hidden crease (concave)");
    }
  } else if (attrs.foldType) {
    lines.push(`${attrs.foldType} fold`);
  }

  lines.push("Seam editing coming soon — inspect only");
  return lines.join("\n");
}
