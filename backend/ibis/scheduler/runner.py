"""Runs the jobs: one asyncio loop per job, started and stopped with the API (see main.py lifespan)."""
import asyncio
import logging
import time
import zlib
from contextlib import contextmanager, suppress
from typing import Iterator, Optional

from sqlalchemy import text

from db.session import SessionLocal, engine
from scheduler.jobs import JOBS, Job

log = logging.getLogger("ibis.scheduler")


@contextmanager
def _single_run(job: Job) -> Iterator[bool]:
    """Yields False if another process is already running this job (Postgres advisory lock).

    Protects against two API instances (or a manual `python -m scheduler`) running the same job
    at once. On SQLite (tests) there is one process, so it always yields True.
    """
    if engine.dialect.name != "postgresql":
        yield True
        return
    key = zlib.crc32(f"ibis.scheduler.{job.name}".encode())
    with engine.connect() as connection:
        got = connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key}).scalar()
        try:
            yield bool(got)
        finally:
            if got:
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                connection.commit()


def run_job(job: Job) -> bool:
    """Run a job once, now, in this thread. Returns False if it was skipped (already running elsewhere)."""
    with _single_run(job) as ok:
        if not ok:
            log.info("Job %s is already running elsewhere; skipped", job.name)
            return False
        started = time.monotonic()
        db = SessionLocal()
        try:
            job.run(db)
        finally:
            db.close()
        log.debug("Job %s took %.2fs", job.name, time.monotonic() - started)
        return True


def find_job(name: str) -> Optional[Job]:
    return next((job for job in JOBS if job.name == name), None)


class Scheduler:
    """Starts a loop per enabled job. Errors are logged and the loop keeps going."""

    def __init__(self, jobs: Optional[list[Job]] = None):
        self.jobs = jobs if jobs is not None else JOBS
        self.tasks: list[asyncio.Task] = []

    def start(self) -> None:
        for job in self.jobs:
            if job.enabled():
                self.tasks.append(asyncio.create_task(self._loop(job), name=f"scheduler:{job.name}"))
                log.info("Scheduled %s every %ss", job.name, job.interval_seconds())

    async def stop(self) -> None:
        for task in self.tasks:
            task.cancel()
        for task in self.tasks:
            with suppress(asyncio.CancelledError):
                await task
        self.tasks = []

    async def _loop(self, job: Job) -> None:
        if not job.run_at_start:
            await asyncio.sleep(job.interval_seconds())
        while True:
            try:
                await asyncio.to_thread(run_job, job)
            except Exception:  # keep the loop alive; the next run tries again
                log.exception("Job %s failed", job.name)
            await asyncio.sleep(job.interval_seconds())
