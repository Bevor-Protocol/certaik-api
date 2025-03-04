from arq import create_pool
from fastapi import APIRouter, Response, status
from fastapi.openapi.docs import get_redoc_html
from fastapi.responses import JSONResponse, RedirectResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from tortoise import Tortoise

from app.config import redis_settings


class BaseRouter:
    def __init__(self):
        self.router = APIRouter(include_in_schema=False)
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route("/", self.read_root, methods=["GET"])
        self.router.add_api_route("/health", self.health_check, methods=["GET"])
        self.router.add_api_route("/metrics", self.get_metrics, methods=["GET"])
        self.router.add_api_route("/test", self.test, methods=["GET"])
        self.router.add_api_route("/docs", self.redoc, methods=["GET"])
        self.router.add_api_route("/redoc", self.redirect_to_docs, methods=["GET"])

    async def read_root(self):
        return {"Hello": "World"}

    async def health_check(self):
        try:
            await Tortoise.get_connection("default").execute_query("SELECT 1;")
            return JSONResponse({"ok": True})
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)})

    async def test(self):
        redis_pool = await create_pool(redis_settings)
        job = await redis_pool.enqueue_job(
            "mock",
        )

        return JSONResponse(
            {"ok": True, "job_id": job.job_id}, status_code=status.HTTP_200_OK
        )

    async def redoc(self):
        return get_redoc_html(
            openapi_url="/openapi.json",
            title="BevorAI API - Docs",
            redoc_favicon_url="https://app.bevor.ai/favicon.ico",
        )

    async def redirect_to_docs(self):
        return RedirectResponse(url="/docs")

    async def get_metrics(self):
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
