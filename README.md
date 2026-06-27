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
```

## Prerequisites

- **Node.js** 20+
- **Python** 3.11+
- **npm**

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

```bash
npm run dev
```

**Option B — separately:**

```bash
# Terminal 1 — API (port 8000)
cd apps/api
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Web (port 3000)
cd apps/web
npm run dev
```

Open:

- Frontend: http://localhost:3000
- Studio: http://localhost:3000/studio
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## MVP Progress

| Step | Status | Description |
|------|--------|-------------|
| 1 | ✅ Done | Project init, monorepo, README, basic API |
| 2 | ✅ Done | Homepage, Studio UI, placeholders |
| 3 | 🔜 Next | Model upload integration |
| 4 | 🔜 | 3D preview (Three.js) |
| 5 | 🔜 | Geometry processing pipeline |
| 6 | 🔜 | End-to-end generate & download |
| 7 | 🔜 | Craftability score |
| 8 | 🔜 | Polish & ZIP export |

## API Endpoints (MVP)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/upload-model` | Upload OBJ / STL / GLB |
| POST | `/api/process-model` | Process model (stub) |
| GET | `/api/projects/:id` | Get project |
| GET | `/api/projects/:id/export/pdf` | Download PDF |
| GET | `/api/projects/:id/export/svg` | Download SVG |
| GET | `/api/projects/:id/export/zip` | Download ZIP |

## Tech Stack

- **Frontend:** Next.js 16, React, TypeScript, Tailwind CSS, shadcn/ui, Zustand
- **Backend:** FastAPI, Pydantic, Trimesh (Step 5+)
- **Storage:** Local filesystem (`storage/`)

## License

Private — MVP development.
