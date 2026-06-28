"""SSE streams for async job progress."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.auth import verify_api_key
from app.services.ai.job_response import build_generation_job_response
from app.services.ai.job_store import generation_job_store
from app.services.job_events import is_terminal_status, job_event_hub
from app.services.process_job_response import build_process_job_response
from app.services.process_job_store import process_job_store
from app.utils.sse import format_sse_comment, format_sse_data

router = APIRouter()

_POLL_SEC = 2.0
_HEARTBEAT_SEC = 15.0


def load_job_snapshot(job_id: str) -> dict | None:
    process_job = process_job_store.get(job_id)
    if process_job is not None:
        return build_process_job_response(process_job).model_dump(mode="json", by_alias=True)

    generation_job = generation_job_store.get(job_id)
    if generation_job is not None:
        return build_generation_job_response(generation_job).model_dump(
            mode="json",
            by_alias=True,
        )

    return None


def _fingerprint(payload: dict) -> tuple:
    return (
        payload.get("status"),
        payload.get("progress"),
        payload.get("message"),
    )


async def _job_event_stream(
    job_id: str,
    request: Request,
    *,
    reload_snapshot: Callable[[str], dict | None],
) -> AsyncIterator[str]:
    last_print: tuple | None = None

    def emit(payload: dict) -> str | None:
        nonlocal last_print
        fp = _fingerprint(payload)
        if fp == last_print:
            return None
        last_print = fp
        return format_sse_data(payload)

    initial = reload_snapshot(job_id)
    if initial is None:
        return

    if chunk := emit(initial):
        yield chunk

    if is_terminal_status(initial.get("status")):
        return

    queue = await job_event_hub.subscribe(job_id)
    loop = asyncio.get_running_loop()
    last_heartbeat = loop.time()

    try:
        while True:
            if await request.is_disconnected():
                break

            try:
                update = await asyncio.wait_for(queue.get(), timeout=_POLL_SEC)
            except asyncio.TimeoutError:
                fresh = reload_snapshot(job_id)
                if fresh is not None:
                    if chunk := emit(fresh):
                        yield chunk
                    if is_terminal_status(fresh.get("status")):
                        break

                now = loop.time()
                if now - last_heartbeat >= _HEARTBEAT_SEC:
                    yield format_sse_comment("keepalive")
                    last_heartbeat = now
                continue

            if chunk := emit(update):
                yield chunk
            if is_terminal_status(update.get("status")):
                break
    finally:
        await job_event_hub.unsubscribe(job_id, queue)


@router.get("/jobs/{job_id}/events")
async def stream_job_events(job_id: str, request: Request) -> StreamingResponse:
    """Stream job progress as Server-Sent Events (fallback: poll GET /jobs/{id})."""
    verify_api_key(request)
    if load_job_snapshot(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    async def generate() -> AsyncIterator[str]:
        async for chunk in _job_event_stream(
            job_id,
            request,
            reload_snapshot=load_job_snapshot,
        ):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/process-jobs/{job_id}/events")
async def stream_process_job_events(job_id: str, request: Request) -> StreamingResponse:
    verify_api_key(request)
    if process_job_store.get(job_id) is None:
        raise HTTPException(status_code=404, detail="Process job not found.")

    def reload_process(job_id: str) -> dict | None:
        job = process_job_store.get(job_id)
        if job is None:
            return None
        return build_process_job_response(job).model_dump(mode="json", by_alias=True)

    async def generate() -> AsyncIterator[str]:
        async for chunk in _job_event_stream(job_id, request, reload_snapshot=reload_process):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/generation-jobs/{job_id}/events")
async def stream_generation_job_events(job_id: str, request: Request) -> StreamingResponse:
    verify_api_key(request)
    if generation_job_store.get(job_id) is None:
        raise HTTPException(status_code=404, detail="Generation job not found.")

    def reload_generation(job_id: str) -> dict | None:
        job = generation_job_store.get(job_id)
        if job is None:
            return None
        return build_generation_job_response(job).model_dump(mode="json", by_alias=True)

    async def generate() -> AsyncIterator[str]:
        async for chunk in _job_event_stream(job_id, request, reload_snapshot=reload_generation):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
