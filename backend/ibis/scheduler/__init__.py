"""Scheduler: everything Ibis does on a timer instead of in reply to a request.

- `jobs.py`   WHAT runs and how often (the job list). Add new periodic work there.
- `runner.py` HOW it runs: one asyncio loop per job inside the API process, each run in a thread
              with its own database session, never two runs of a job at once.

Jobs only call services; the rules stay in `services/` and `domain/`. Requests never run jobs.
Run one by hand with `python -m scheduler <job>` (from backend/ibis), e.g. `python -m scheduler housekeeping`.
"""
from scheduler.jobs import JOBS, Job
from scheduler.runner import Scheduler, run_job

__all__ = ["JOBS", "Job", "Scheduler", "run_job"]
