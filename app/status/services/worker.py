from fastapi import HTTPException
from rq.registry import FailedJobRegistry

from app.cache import redis_client
from app.queues import queue_high

MAX_RETRIES = 3


def fetch_job_status(job_id: str):
    cur_retry_counter = redis_client.get("retries|{job_id}")
    if cur_retry_counter:
        cur_retry_counter = int(cur_retry_counter.decode("utf-8"))
        if cur_retry_counter >= 3:
            return {"status": "failed", "allow_retry": False}
    job = queue_high.fetch_job(job_id)
    if job:
        status = job.get_status()
        result = job.result
        return {"status": status, "result": result, "allow_retry": True}
    raise HTTPException(status_code=400, detail="This job does not exist")


def retry_failed_job(job_id):
    registry = FailedJobRegistry(queue=queue_high)
    cur_retry_counter = redis_client.get("retries|{job_id}")
    if cur_retry_counter:
        cur_retry_counter = int(cur_retry_counter.decode("utf-8"))
        if cur_retry_counter >= 3:
            return {"success": False}

    for job_id_found in registry.get_job_ids():
        if job_id == job_id_found:
            registry.requeue(job_or_id=job_id, at_front=True)
            redis_client.incr("retries|{job_id}")
            return {"success": True}
    return {"success": False}
