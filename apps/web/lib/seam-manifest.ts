import { withStorageAuth } from "@/lib/api-auth";

export type SeamEdgeKind = "cut" | "fold";

export type SeamPosition3d = {
  a: [number, number, number];
  b: [number, number, number];
};

export type SeamEdgeInfo = {
  kind: SeamEdgeKind;
  pieceId: string;
  pieceLabel: string;
  lineId: string;
  foldType?: "mountain" | "valley";
  dihedralDeg: number;
  signedDihedralDeg: number;
  hiddenCrease: boolean;
  inSeamSet?: boolean;
  hasOverlap?: boolean;
  position3d?: SeamPosition3d;
};

export type SeamEdgeHint = {
  toggleValid: boolean;
  error?: string;
  overlapPiecesAfter?: number;
  pieceCountAfter?: number;
};

export type SeamSuggestion = {
  meshEdge: string;
  action: "add" | "remove";
  score: number;
  label: string;
  reason?: string;
};

export type SeamAiSuggestion = {
  action: "split" | "merge";
  piece_labels: string[];
  reason: string;
};

export type SeamAiHints = {
  model_interpretation?: string;
  structural_notes?: string;
  suggestions?: SeamAiSuggestion[];
  assembly_order_hint?: string;
};

export type SeamAdvisor = {
  overlapPieces: string[];
  suggestions: SeamSuggestion[];
  edgeHints: Record<string, SeamEdgeHint>;
  faceHeat?: Record<string, number>;
  guidance?: string[];
  aiHints?: SeamAiHints | null;
};

export type SeamManifest = {
  version: number;
  edgeCount: number;
  activeSeams: string[];
  edges: Record<string, SeamEdgeInfo>;
  advisor: SeamAdvisor | null;
};

export function seamManifestUrls(projectId: string) {
  const json = `/storage/exports/${projectId}.seams.json`;
  const api = `/api/projects/${projectId}/seams`;
  return {
    json,
    jsonAuth: withStorageAuth(json),
    api,
  };
}

export function seamManifestPreviewUrl(projectId: string, revision: number): string {
  const { jsonAuth } = seamManifestUrls(projectId);
  const separator = jsonAuth.includes("?") ? "&" : "?";
  return `${jsonAuth}${separator}v=${revision}`;
}

function parsePosition3d(raw: unknown): SeamPosition3d | undefined {
  if (!raw || typeof raw !== "object") {
    return undefined;
  }
  const value = raw as Record<string, unknown>;
  const a = value.a;
  const b = value.b;
  if (!Array.isArray(a) || !Array.isArray(b) || a.length !== 3 || b.length !== 3) {
    return undefined;
  }
  return {
    a: [Number(a[0]), Number(a[1]), Number(a[2])],
    b: [Number(b[0]), Number(b[1]), Number(b[2])],
  };
}

function parseSeamAiHints(raw: unknown): SeamAiHints | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const value = raw as Record<string, unknown>;
  const suggestions = Array.isArray(value.suggestions)
    ? value.suggestions
        .map((item) => {
          if (!item || typeof item !== "object") return null;
          const suggestion = item as Record<string, unknown>;
          const action = suggestion.action === "merge" ? "merge" : "split";
          const pieceLabels = Array.isArray(suggestion.piece_labels)
            ? suggestion.piece_labels.map(String)
            : [];
          const reason = suggestion.reason ? String(suggestion.reason) : "";
          if (!reason) return null;
          return { action, piece_labels: pieceLabels, reason } satisfies SeamAiSuggestion;
        })
        .filter((item): item is SeamAiSuggestion => item !== null)
    : [];

  return {
    model_interpretation: value.model_interpretation
      ? String(value.model_interpretation)
      : undefined,
    structural_notes: value.structural_notes
      ? String(value.structural_notes)
      : undefined,
    suggestions,
    assembly_order_hint: value.assembly_order_hint
      ? String(value.assembly_order_hint)
      : undefined,
  };
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
      inSeamSet: Boolean(edge.inSeamSet),
      hasOverlap: Boolean(edge.hasOverlap),
      position3d: parsePosition3d(edge.position3d),
    };
  }

  let advisor: SeamAdvisor | null = null;
  if (payload.advisor && typeof payload.advisor === "object") {
    const rawAdvisor = payload.advisor as Record<string, unknown>;
    const suggestions = Array.isArray(rawAdvisor.suggestions)
      ? rawAdvisor.suggestions
          .map((item) => {
            if (!item || typeof item !== "object") return null;
            const s = item as Record<string, unknown>;
            const suggestion: SeamSuggestion = {
              meshEdge: String(s.meshEdge ?? ""),
              action: s.action === "remove" ? "remove" : "add",
              score: Number(s.score ?? 0),
              label: String(s.label ?? ""),
              reason: s.reason ? String(s.reason) : undefined,
            };
            return suggestion.meshEdge.length > 0 ? suggestion : null;
          })
          .filter((item): item is SeamSuggestion => item !== null)
      : [];
    const edgeHints: Record<string, SeamEdgeHint> = {};
    if (rawAdvisor.edgeHints && typeof rawAdvisor.edgeHints === "object") {
      for (const [key, value] of Object.entries(
        rawAdvisor.edgeHints as Record<string, unknown>,
      )) {
        if (!value || typeof value !== "object") continue;
        const hint = value as Record<string, unknown>;
        edgeHints[key] = {
          toggleValid: Boolean(hint.toggleValid),
          error: hint.error ? String(hint.error) : undefined,
          overlapPiecesAfter:
            hint.overlapPiecesAfter !== undefined
              ? Number(hint.overlapPiecesAfter)
              : undefined,
          pieceCountAfter:
            hint.pieceCountAfter !== undefined
              ? Number(hint.pieceCountAfter)
              : undefined,
        };
      }
    }
    advisor = {
      overlapPieces: Array.isArray(rawAdvisor.overlapPieces)
        ? rawAdvisor.overlapPieces.map(String)
        : [],
      suggestions,
      edgeHints,
      faceHeat:
        rawAdvisor.faceHeat && typeof rawAdvisor.faceHeat === "object"
          ? Object.fromEntries(
              Object.entries(rawAdvisor.faceHeat as Record<string, unknown>).map(
                ([key, value]) => [key, Number(value)],
              ),
            )
          : undefined,
      guidance: Array.isArray(rawAdvisor.guidance)
        ? rawAdvisor.guidance.map(String)
        : undefined,
      aiHints: parseSeamAiHints(rawAdvisor.aiHints),
    };
  }

  return {
    version: Number(payload.version ?? 0),
    edgeCount: Number(payload.edgeCount ?? Object.keys(edges).length),
    activeSeams: Array.isArray(payload.activeSeams)
      ? payload.activeSeams.map(String)
      : [],
    edges,
    advisor,
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

export function parseSeamLineId(id: string | null | undefined): {
  edgeKind: string;
  pieceLabel: string;
  meshEdge: string | null;
  foldType: string | null;
} | null {
  if (!id) {
    return null;
  }
  const match = /^seam-(cut|fold)-([A-Za-z0-9]+)-(\d+)-(\d+)(?:-(mountain|valley))?$/.exec(id);
  if (!match) {
    return null;
  }
  const [, edgeKind, pieceLabel, v0, v1, foldType] = match;
  return {
    edgeKind,
    pieceLabel,
    meshEdge: normalizeMeshEdgeKey(`${v0},${v1}`),
    foldType: foldType ?? null,
  };
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
  const fromId = parseSeamLineId(line.id);
  if (fromId?.meshEdge) {
    return {
      edgeKind: fromId.edgeKind,
      pieceId: "",
      pieceLabel: fromId.pieceLabel,
      meshEdge: fromId.meshEdge,
      lineId: line.id,
      foldType: fromId.foldType,
    };
  }

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
  edgeHint?: SeamEdgeHint,
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
    if (manifestEdge.hasOverlap) {
      lines.push("This piece has unfold overlap");
    }
  } else if (attrs.foldType) {
    lines.push(`${attrs.foldType} fold`);
  }

  if (edgeHint) {
    if (!edgeHint.toggleValid && edgeHint.error) {
      lines.push(`Cannot toggle: ${edgeHint.error}`);
    } else if (edgeHint.toggleValid && edgeHint.overlapPiecesAfter !== undefined) {
      lines.push(
        `After toggle: ${edgeHint.overlapPiecesAfter} overlapping piece(s), ${edgeHint.pieceCountAfter ?? "?"} total`,
      );
    }
  }

  lines.push(
    attrs.edgeKind === "fold"
      ? "Click “Split here” to cut along this edge."
      : "Click “Merge pieces” to remove this cut seam.",
  );
  return lines.join("\n");
}
