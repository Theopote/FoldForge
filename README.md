# FoldForge / 纸模工坊

**Turn imagination into printable paper models.**  
把想象折成立体。

FoldForge is an AI-powered papercraft generation platform. Upload a 3D model and get a printable template with cut lines, fold lines, glue tabs, and part numbers.

## Monorepo Structure

```txt
foldforge/
  apps/
    web/          # Next.js frontend
    api/          # FastAPI backend
  packages/
    shared/types/ # Shared TypeScript types
  storage/
    uploads/      # Uploaded 3D models
    processed/    # Cleaned / simplified meshes
    exports/      # SVG, PDF, ZIP outputs
  docs/           # Product & architecture docs
  docker-compose.yml
```

## Prerequisites

- **Node.js** 20+
- **Python** 3.11+
- **npm**
- **Docker Desktop** (optional, for production-like local deployment)

Before a demo or release validation, run:

```bash
npm run doctor
```

`doctor` checks Node/npm, Python, Docker, frontend/API ports, and API health so broken local environments fail loudly.

## Quick Start

### 1. Install dependencies

```bash
# Root (concurrent dev scripts)
npm install

# Frontend
npm install --prefix apps/web

# Backend
cd apps/api
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp apps/web/.env.local.example apps/web/.env.local
```

### 3. Run development servers

**Option A — both at once (from repo root):**

Activate the API virtualenv first (step 1), then:

```bash
npm run dev
```

`dev:api` uses `python -m uvicorn` (same as option B), so the shell must resolve `python` to your activated `apps/api/.venv`.

**Option B — separately:**

```bash
# Terminal 1 — API (port 8000)
cd apps/api
python -m uvicorn app.main:app --reload --reload-dir app --reload-delay 0.4 --host 0.0.0.0 --port 8000

# Terminal 2 — Web (port 3000)
cd apps/web
npm run dev
```

Open:

- Frontend: http://localhost:3000
- Studio: http://localhost:3000/studio
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

### Docker Compose (production-like single host)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose v2).

```bash
# Optional: API key / AI provider
cp .env.docker.example .env

docker compose up --build
```

- Studio: http://localhost:3000  
- API docs: http://localhost:8000/docs  
- Data: Docker volume `foldforge-storage` (SQLite + uploads/exports)

Reset all data: `docker compose down -v`

For hot reload during development, use the native *Quick Start* above instead of Docker.

Planned improvements (SSE job stream, interactive seam editor, texture baking) are evaluated in [`docs/future-features.md`](docs/future-features.md).

## Supported formats

| Input | Status | Notes |
|-------|--------|-------|
| OBJ, STL, GLB, GLTF | **Stable** | Recommended for upload → papercraft pipeline |
| FBX | **Experimental** | Rejected at upload in MVP (unreliable Trimesh import) |
| Text → 3D | **Experimental** | Requires configured AI provider (`AI_PROVIDER`, API keys) |
| Image → 3D | **Experimental** | Same as text; quality varies by provider |

Exports: **PDF** (with 50 mm scale check + legend), **SVG**, **ZIP** (includes `README.txt`, `instructions.txt`, and `instructions.pdf` with piece inventory and tab pairings).

Projects and async jobs are persisted in **SQLite** (`storage/foldforge.db`) so a backend restart does not lose project metadata. The Studio UI loads project state from the API on open; the browser only remembers the last project id (`localStorage` + optional `/studio?project=` URL).

## Papercraft layout policy

FoldForge **never scales individual paper pieces** to force them onto a page. All parts stay at the same model scale so glue tabs and edges remain aligned.

Export is blocked when the layout is unsafe:

- **Oversize piece** — rotated bounding box exceeds the printable area for the selected paper.
- **Unplaced piece** — a part passes size checks but cannot be placed (invalid geometry, packing failure, etc.).
- **Page overlap** — pieces overlap on the sheet after auto-repair retries.

Errors name the affected piece labels and suggest **A3**, lowering **target height** (uniform model scale), or **Easy mode** to split into smaller patches.

## Job cancellation

Cancel is **best-effort cooperative**: the API marks queued jobs cancelled immediately and sets `cancelRequested` on running jobs. The pipeline checks cancellation at stage boundaries and inside long unfold/layout/NFP loops, then raises `JobCancelledError` as soon as possible.

Cancel on an already **completed**, **failed**, or **cancelled** job returns the current job state (no 409) so the Studio UI can recover cleanly.

Aborting the frontend poll (`AbortSignal`) stops status updates locally; use **Cancel processing** to stop backend work. A cancelled job does not mark the project `ready` or write export URLs.

## MVP Progress

| Step | Status | Description |
|------|--------|-------------|
| 1 | ✅ Done | Project init, monorepo, README, basic API |
| 2 | ✅ Done | Homepage, Studio UI, sample cases |
| 3 | ✅ Done | Model upload + project ID |
| 4 | ✅ Done | 3D preview (OBJ/STL/GLB) + mesh stats |
| 5 | ✅ Done | Geometry pipeline + SVG/PDF export |
| 6 | ✅ Done | End-to-end generate, preview, download |
| 7 | ✅ Done | Craftability score + warnings UI |
| 8 | ✅ Done | ZIP export, localStorage, project page |
| **Phase 2** | ✅ | Text/Image to 3D + AI providers |

## API Endpoints (MVP)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/upload-model` | Upload OBJ / STL / GLB / GLTF |
| POST | `/api/generate-from-text` | AI text → 3D (**experimental**) |
| POST | `/api/generate-from-image` | AI image → 3D (**experimental**) |
| GET | `/api/ai/providers` | List AI providers |
| POST | `/api/process-model` | Queue papercraft job → returns `jobId` (202) |
| GET | `/api/process-jobs/{jobId}` | Poll process job status / result |
| GET | `/api/process-jobs/{jobId}/events` | **SSE** process job progress |
| GET | `/api/jobs/{jobId}/events` | **SSE** any async job (unified) |
| POST | `/api/process-jobs/{jobId}/cancel` | Cancel queued job or request stop for running job |
| GET | `/api/projects/:id` | Get project |
| PATCH | `/api/projects/:id/settings` | Save papercraft settings (Studio sync) |
| GET | `/api/projects/:id/export/pdf` | Download PDF |
| GET | `/api/projects/:id/export/svg` | Download SVG |
| GET | `/api/projects/:id/export/zip` | Download ZIP |

## Tech Stack

- **Frontend:** Next.js 16, React, TypeScript, Tailwind CSS, shadcn/ui, Zustand
- **Backend:** FastAPI, Pydantic, Trimesh (Step 5+)
- **Storage:** Local filesystem (`storage/`)

## Testing

From the repo root (API venv activated):

```bash
# Install API test dependencies once
pip install -r apps/api/requirements-dev.txt

# Generate mesh fixtures (committed in CI; run locally after clone)
python apps/api/tests/fixtures/generate_fixtures.py

# All tests: backend pytest + frontend production build
npm run test

# Backend only
npm run test:api

# API upload → process e2e (slower)
npm run test:api:e2e
```

Backend tests live under `apps/api/tests/`:

- **Unit** — geometry algorithms, upload validation, model loading
- **Pipeline snapshots** — `cube.stl`, `low_poly_bunny.obj`, `simple_house.glb`, `thin_parts_model.obj`
- **Export** — SVG/PDF/ZIP structure and page sizing
- **Integration** — upload + async process job via FastAPI

Pipeline snapshot tests patch in a fast row layout (NFP nesting is covered separately in unit tests) so CI stays under a few minutes. Models with more than **24 pieces** (typical on Advanced difficulty) automatically use shelf packing in production instead of exact NFP.

Refresh pipeline snapshots after intentional geometry changes:

```bash
cd apps/api
UPDATE_SNAPSHOTS=1 python -m pytest tests/pipeline/test_pipeline_snapshots.py
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `npm run dev` — API won't start | Virtualenv not activated | Activate `apps/api/.venv` so `python` finds uvicorn |
| `python` not found / wrong version | System Python vs venv | Use `python3` on macOS/Linux; create venv per Quick Start |
| Upload returns 400 for FBX | FBX not supported in MVP | Convert to OBJ, STL, or GLB |
| Generate hangs / times out | Long-running unfold or layout | Check `/api/process-jobs/{jobId}`; try **Easy** mode or cancel the job |
| **Piece too large for paper** | Target height or paper size | Error names the piece and paper, e.g. try **A3** or reduce **target height**; Easy mode splits into smaller parts |
| **Could not place piece(s)** | Invalid cut outline or packing failure | Piece label appears in the error; try **A3**, lower **target height**, or **Easy mode**; check mesh quality |
| Cancel clicked but UI stuck on processing | Job finished at the same time as cancel | Reload project or open process job — terminal jobs return current state; completed jobs show results |
| Cancel does not stop instantly | Heavy stage already running | Cancel is checked between pipeline steps and inside unfold/layout loops; wait a few seconds |
| Piece scaled / misaligned tabs | Old build or manual edit | Current FoldForge does not per-piece scale; regenerate after changing paper or height |
| Project 404 after restart | Stale project id in URL or localStorage | Open `/studio` for a fresh session, or `/studio?project={id}` when the backend DB still has that project |
| Studio out of sync across tabs | Another tab switched projects | Reload Studio — project state is loaded from the API; tabs share only the last project id |
| Empty PDF / SVG | Process job failed | Open job error message; try a simpler mesh (e.g. `cube.stl`) |
| Text/Image → 3D fails | No AI provider configured | Set `AI_PROVIDER=mock` for demo or configure Meshy/Replicate keys |

## License

Private — MVP development.
