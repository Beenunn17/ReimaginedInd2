"""RQ worker entrypoint for MMM training jobs.

This module connects to a Redis instance using connection details from
environment variables and listens on the `mmm` queue. When jobs are
submitted by the API (e.g., via `/mmm/train`), they are executed in this
worker process. The tasks themselves are defined in
`agents.data_science_agent.train_and_cache_mmm_job`.
"""

from __future__ import annotations

import os
from rq import Worker, Queue
from redis import Redis

# Connect to Redis
redis = Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379))
)

# Queue names to listen on (default to "mmm")
listen = [os.getenv("RQ_QUEUES", "mmm")]

if __name__ == "__main__":
    q = Queue(listen[0], connection=redis)
    Worker([q], connection=redis).work(with_scheduler=True)


def run_worker() -> None:
    """Start an RQ worker listening on the 'mmm' queue."""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))
    conn = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
    # Only listen to the mmm queue
    listen_queues = [Queue("mmm")]
    with Connection(conn):
        worker = Worker(listen_queues)
        worker.work()


if __name__ == "__main__":
    run_worker()