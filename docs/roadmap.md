# FoldForge Roadmap

## Phase 1 — MVP ✅

- [x] Monorepo + Next.js + FastAPI scaffold
- [x] Homepage + Studio UI
- [x] Upload → project ID
- [x] Three.js 3D preview
- [x] Mesh pipeline (clean, simplify, unfold)
- [x] SVG / PDF export
- [x] End-to-end generate & download
- [x] Craftability score + warnings
- [x] ZIP download + project restore

## Phase 2 — AI Input ✅

- [x] Text-to-3D API + Studio tab
- [x] Image-to-3D API + Studio tab
- [x] Pluggable AI provider layer (mock + Replicate)
- [x] Papercraft-optimized prompt enhancement
- [ ] Production TripoSR / Meshy integration tuning

## Phase 3 — Maker Experience

Priority order (updated — see also `docs/future-features.md`):

1. **Texture / color baking** — highest visual impact; extend existing `colorMode` into baked piece fills
2. Interactive **SVG seam editor** (drag seams → incremental re-unfold)
3. ~~**SSE job progress**~~ — prototype: `/api/jobs/{id}/events`, EventSource + poll fallback
4. ~~**Assembly instruction generator**~~ — `instructions.txt` + `instructions.pdf` with piece inventory, tab pairings, color-mode notes, Chinese summary
5. Paper thickness compensation
6. Community templates & sharing
7. User accounts & project history

## Phase 4 — Pro Tools

- Blender headless advanced cleanup
- CNC / laser DXF export
- Batch processing API
