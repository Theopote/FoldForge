# Texture Baking Spike

Status: **prototype** — validates the color pipeline end-to-end in SVG and PDF export.

## Goal

Map source mesh surface appearance onto unfolded 2D triangles so `colorMode=color` produces printable fills instead of line art only.

## Approach

```text
3D mesh face
  → sample RGB (vertex colors → texture UV → normal tint fallback)
  → map face corners through unfold vertex map (same as cut/fold geometry)
  → BakedTriangle(a, b, c, fill="#rrggbb")
  → SVG / PDF polygon under cut/fold layers
```

Implementation: `app/services/texture_baker.py`

## Supported inputs (spike)

| Source | Status |
|--------|--------|
| Vertex colors | ✅ Primary path |
| GLB/GLTF texture + UV | ✅ Basic PIL sampling at vertex UV |
| No color data | ✅ Normal-direction gray tint (placeholder) |

## Not in spike

- Per-piece raster PNG clip paths (vector triangles chosen for print sharpness)
- AI-generated material recovery
- Paper stock simulation (kraft / cardstock presets)
- Baking through tab/cut-outline boolean (fills use unfold triangles only)

**PDF color fills:** implemented in `pdf_exporter.py` (same triangle layer as SVG, 92% opacity).

**Studio preview:** unfold panel renders the exported SVG (includes baked fills when `colorMode=color`), with storage auth, cache-bust revision, and stale-preview hint when settings change after export.

**Material cache:** geometry + face colors persisted under `storage/cache/`; unchanged geometry settings skip unfold/tabs on regenerate (layout-only changes).

## Pipeline hook

When `ProjectSettings.colorMode == "color"`:

1. After unfold repair
2. Before tabs/layout
3. `bake_piece_textures(mesh, pieces, dihedral)`

Progress message: `"Baking surface colors"`.

## Tests

- `tests/unit/test_texture_baker.py`

## Next steps

1. **Raster mode** — optional high-res bake for photo textures (`512px` short edge)
2. **Quality** — barycentric UV sampling + mip-aware filtering for large faces

**Material cache:** `storage/cache/{project_id}.material.json` stores unfold geometry, baked triangles, and per-face fill colors. When source + geometry settings are unchanged, the pipeline skips unfold/tabs and re-runs layout + export only (e.g. paper size change). Face-color cache avoids re-sampling mesh textures on color rebake.

## Risks

- Re-running `compute_unfold_vertex_map` per piece duplicates unfold work (acceptable for spike; cache vertex maps on `UnfoldPiece` later)
- Texture seams at patch boundaries will not align until global UV unification
- Large SVG file size when many colored triangles (consider raster fallback threshold)
