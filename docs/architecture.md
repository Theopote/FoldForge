# FoldForge Architecture

## High-Level Flow

```mermaid
flowchart LR
  A[Upload 3D] --> B[Mesh Clean]
  B --> C[Simplify]
  C --> D[Seam Selection]
  D --> E[Unfold Patches]
  E --> F[Tabs + Labels]
  F --> G[Page Layout]
  G --> H[SVG / PDF Export]
```

## Apps

### `apps/web`

Next.js App Router frontend. Proxies `/api/*` and `/storage/*` to FastAPI via `next.config.ts` rewrites.

State: Zustand (`store/studio-store.ts`).

### `apps/api`

FastAPI service with modular routers and geometry services.

| Layer | Responsibility |
|-------|----------------|
| `routers/` | HTTP endpoints |
| `schemas/` | Pydantic request/response models |
| `services/` | Business & geometry logic |
| `utils/` | File I/O, logging, geometry helpers |

MVP uses SQLite-backed `ProjectStore` and `GenerationJobStore` (`storage/foldforge.db`). PostgreSQL can replace SQLite when multi-instance deployment is needed.

## Storage

```
storage/
  uploads/     {projectId}.glb
  processed/   {projectId}_processed.glb
  exports/     {projectId}.svg, {projectId}.pdf
```

Served at `/storage/*` via FastAPI `StaticFiles`.

## Extensibility

Geometry services (`unfolder.py`, `seam_generator.py`, etc.) provide the current papercraft pipeline behind clear module boundaries, so stronger algorithms can swap in without changing API contracts.
