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

## Get Project

```http
GET /api/projects/:id
```

## Export

```http
GET /api/projects/:id/export/pdf
GET /api/projects/:id/export/svg
GET /api/projects/:id/export/zip
```

Interactive docs: `/docs`
