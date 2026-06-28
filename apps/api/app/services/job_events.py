"""In-process pub/sub for async job progress (SSE prototype)."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from app.utils.logging_utils import get_logger

logger = get_logger(__name__)

_TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})


class JobEventHub:
    """Broadcast job snapshot updates to SSE subscribers on the API event loop."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def publish(self, job_id: str, payload: dict[str, Any]) -> None:
        loop = self._loop
        if loop is None or not loop.is_running():
            return
        try:
            asyncio.run_coroutine_threadsafe(self._broadcast(job_id, payload), loop)
        except RuntimeError:
            logger.debug("Skipped job event publish for %s (no running loop)", job_id)

    async def _broadcast(self, job_id: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            queues = list(self._subscribers.get(job_id, []))
        for queue in queues:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(payload)
                except asyncio.QueueFull:
                    pass

    async def subscribe(self, job_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=32)
        async with self._lock:
            self._subscribers[job_id].append(queue)
        return queue

    async def unsubscribe(self, job_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            subs = self._subscribers.get(job_id, [])
            if queue in subs:
                subs.remove(queue)
            if not subs:
                self._subscribers.pop(job_id, None)


job_event_hub = JobEventHub()


def notify_process_job(job) -> None:
    from app.services.process_job_response import build_process_job_response

    payload = build_process_job_response(job).model_dump(mode="json", by_alias=True)
    job_event_hub.publish(job.id, payload)


def notify_generation_job(job) -> None:
    from app.services.ai.job_response import build_generation_job_response

    payload = build_generation_job_response(job).model_dump(mode="json", by_alias=True)
    job_event_hub.publish(job.id, payload)


def is_terminal_status(status: str | None) -> bool:
    return status in _TERMINAL_STATUSES
