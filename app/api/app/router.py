from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Response, status
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from tortoise.exceptions import DoesNotExist

from app.api.core.dependencies import Authentication, AuthenticationWithoutDelegation
from app.api.services.app import AppService
from app.utils.constants.openapi_tags import APP_TAG
from app.utils.openapi import OPENAPI_SPEC
from app.utils.schema.dependencies import AuthState
from app.utils.schema.request import AppUpsertBody
from app.utils.types.enums import AuthRequestScopeEnum


class AppRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/app", tags=[APP_TAG])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "",
            self.upsert_app,
            methods=["POST", "PATCH"],
            dependencies=[
                Depends(
                    Authentication(request_scope=AuthRequestScopeEnum.APP_FIRST_PARTY)
                )
            ],
            operation_id="upsert_app",
            include_in_schema=False,
        )
        self.router.add_api_route(
            "/info",
            self.get_app_info,
            methods=["GET"],
            dependencies=[
                Depends(
                    AuthenticationWithoutDelegation(
                        request_scope=AuthRequestScopeEnum.APP
                    )
                )
            ],
            **OPENAPI_SPEC["get_app_info"]
        )
        self.router.add_api_route(
            "/stats",
            self.get_stats,
            methods=["GET"],
            dependencies=[
                Depends(
                    AuthenticationWithoutDelegation(
                        request_scope=AuthRequestScopeEnum.APP_FIRST_PARTY
                    )
                )
            ],
            include_in_schema=False,
        )

    async def upsert_app(
        self, request: Request, body: Annotated[AppUpsertBody, Body()]
    ):
        app_service = AppService()

        if request.method == "POST":
            fct = app_service.create
        if request.method == "PATCH":
            fct = app_service.update

        try:
            response = await fct(auth=request.state.auth, body=body)

            return JSONResponse(
                {"result": response}, status_code=status.HTTP_202_ACCEPTED
            )
        except DoesNotExist as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err)

    async def get_app_info(self, request: Request):
        app_service = AppService()
        auth: AuthState = request.state.auth

        try:
            response = await app_service.get_info(auth.app_id)
            return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)
        except DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="This app does not exist"
            )

    async def get_stats(self, request: Request):
        app_service = AppService()

        response = await app_service.get_stats()

        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)
