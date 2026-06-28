"""Tests for SQLite read concurrency."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from app.db.database import Database


def test_concurrent_reads_do_not_serialize(tmp_path) -> None:
    """Multiple read connections should overlap, not queue behind each other."""
    db = Database(tmp_path / "concurrent.db")
    hold_sec = 0.15
    reader_count = 8

    def slow_read() -> float:
        start = time.monotonic()
        with db.read_connection() as conn:
            conn.execute("SELECT 1").fetchone()
            time.sleep(hold_sec)
        return time.monotonic() - start

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=reader_count) as pool:
        durations = list(pool.map(lambda _: slow_read(), range(reader_count)))
    elapsed = time.monotonic() - started

    # Serialized reads would take ~reader_count * hold_sec.
    assert elapsed < hold_sec * 3
    assert all(duration >= hold_sec * 0.9 for duration in durations)


def test_write_blocks_concurrent_read_until_commit(tmp_path) -> None:
    """An active writer holds exclusive access until the transaction finishes."""
    db = Database(tmp_path / "rw.db")
    write_holding = threading.Event()
    release_write = threading.Event()

    def slow_write() -> None:
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO projects (id, data, created_at, updated_at) "
                "VALUES ('p1', '{}', 't', 't')"
            )
            write_holding.set()
            release_write.wait(timeout=5)

    def read_after_write_starts() -> float:
        write_holding.wait(timeout=5)
        start = time.monotonic()
        with db.read_connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM projects").fetchone()
        return time.monotonic() - start, int(row["c"])

    writer = threading.Thread(target=slow_write)
    writer.start()
    assert write_holding.wait(timeout=5)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(read_after_write_starts)
        time.sleep(0.05)
        assert not future.done()
        release_write.set()
        wait_sec, count = future.result(timeout=5)

    writer.join(timeout=5)
    assert count == 1
    assert wait_sec >= 0.04
