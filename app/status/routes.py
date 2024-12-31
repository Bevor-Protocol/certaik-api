from fastapi import APIRouter

from .services.worker import fetch_job_status, retry_failed_job

router = APIRouter()


@router.get("/job/{job_id}")
def get_job_status(job_id: str):
    response = fetch_job_status(job_id)
    return response


@router.post("/job/retry/{job_id}")
def get_failed_jobs(job_id: str):
    return retry_failed_job(job_id)
