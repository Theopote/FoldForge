# FoldForge API Reference (MVP)

Base URL: `http://localhost:8000`

Frontend proxies requests through `http://localhost:3000/api/*`.

## Health

```http
GET /health
```

```json
{ "status": "ok" }
```

## Upload Model

```http
POST /api/upload-model
Content-Type: multipart/form-data
```

| Field | Type | Description |
|-------|------|-------------|
| file | file | OBJ, STL, GLB, GLTF, FBX |

Response:

```json
{
  "projectId": "abc123",
  "sourceFileUrl": "/storage/uploads/abc123.glb",
  "status": "uploaded"
}
```

## Process Model

```http
POST /api/process-model
Content-Type: application/json
```

Request body matches `ProjectSettings` + `projectId`. Full pipeline implemented in Step 5.

## AI Generate (Phase 2)

```http
POST /api/generate-from-text
Content-Type: application/json

{ "prompt": "A low poly cat", "style": "low_poly" }
```

```http
POST /api/generate-from-image
Content-Type: multipart/form-data
```

Fields: `file`, `style`, optional `hint`, `name`.

```http
GET /api/ai/providers
```

Production providers return **202 Accepted** with `jobId`. Poll:

```http
GET /api/generation-jobs/{jobId}
```

See [ai.md](./ai.md) for provider configuration (Meshy, TripoSR, async queue).

## Get Project

```http
GET /api/projects/:id
```

```http
GET /api/projects/:id/generation-job
```

Returns the latest AI generation job for the project (for resuming async jobs after reload).

## Export

```http
GET /api/projects/:id/export/pdf
GET /api/projects/:id/export/svg
GET /api/projects/:id/export/zip
```

Interactive docs: `/docs`
