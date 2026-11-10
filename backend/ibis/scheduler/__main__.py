"""Run a scheduled job once, by hand: `python -m scheduler <job>` (from backend/ibis). No name lists the jobs."""
import logging
import sys

import models  # noqa: F401  (registers all tables/relationships)
from scheduler.runner import JOBS, find_job, run_job


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO)
    if len(argv) != 1:
        print("Usage: python -m scheduler <job>\nJobs: " + ", ".join(job.name for job in JOBS))
        return 1
    job = find_job(argv[0])
    if job is None:
        print(f"Unknown job '{argv[0]}'. Jobs: " + ", ".join(j.name for j in JOBS))
        return 1
    return 0 if run_job(job) else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
