# Future Features — Evaluation Notes

Product suggestions evaluated against current MVP scope. Items marked **Adopt** are implemented or scheduled; **Defer** need more design or are high-effort.

## Job progress: SSE vs WebSocket vs polling

| Approach | Verdict | Notes |
|----------|---------|-------|
| HTTP polling (current) | **Keep for now** | 1.5s interval, `AbortSignal` cancel, works through Next.js rewrites. Good enough for MVP. |
| SSE job stream | **Adopt — prototype** | `GET /api/jobs/{id}/events` + store push via `job_event_hub`. Frontend uses EventSource with poll fallback. |
| WebSocket | Defer | Bidirectional overhead not needed until collaborative editing or binary streams. |

**Recommended path:** add `GET /api/process-jobs/{id}/events` and `GET /api/jobs/{id}/events` as SSE streams. Worker pushes `{ progress, message, status }` on each DB update; frontend replaces `pollProcessJob` loop with `EventSource` + same terminal handlers. Keep GET poll as fallback for proxies that buffer SSE.

**Not doing now:** SSE requires an in-process pub/sub (or Redis for multi-instance). Current single-worker asyncio queues make SSE straightforward but still a cross-cutting change — track in Phase 3.

## Interactive SVG seam editing

**Phase A + B + C adopted.**

Shipped:

1. **SVG:** `layer-seams` hit targets with seam metadata in element `id`.
2. **Export:** `{projectId}.seams.json` manifest v2 + `{projectId}.seamset.json` authoritative seam set.
3. **Studio:** Seams mode — inspect, **Split here / Merge pieces**, undo, incremental re-unfold.
4. **API:** `PATCH /api/projects/{id}/seams` → async seam reflow job; `GET` returns advisor + 3D positions.
5. **3D sync:** selected seam edge highlighted on processed GLB; overlap pieces glow in SVG.
6. **Advisor:** toggle preview hints, overlap list, ranked seam suggestions.

Next (Phase D):

1. Click-to-select edges directly in 3D view.
2. Live overlap heatmap overlay per face.
3. AI-assisted seam recommendations.

Existing pieces: `unfold_with_custom_seams`, `run_seam_reflow_pipeline`, `apply_seam_toggle`.

## Docker Compose deployment

**Adopted** — see root `docker-compose.yml` and README *Docker* section.

## Texture / color baking

**Adopt — elevated priority within Phase 3.**

**Spike complete** — see `docs/spike-texture-baking.md`. When `colorMode=color`, the pipeline bakes vertex colors / GLB textures onto unfold triangles and renders SVG + PDF polygon fills; Studio unfold preview shows the baked SVG export.

**Remaining for full Phase 3:**

1. Texture baking from source mesh / AI materials → piece SVG fills ✅ (spike)
2. Material cache for layout-only re-export ✅
3. Paper stock presets (kraft, white, colored cardstock)
4. Paper thickness compensation (fold offset)

See `docs/roadmap.md` for updated Phase 3 ordering.
