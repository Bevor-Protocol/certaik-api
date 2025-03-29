from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Request, Response, status

from app.api.admin.service import AdminService
from app.api.dependencies import Authentication
from app.utils.logger import get_logger
from app.utils.schema.dependencies import AuthState
from app.utils.schema.request import (
    AdminQuerySearch,
    CreatePromptBody,
    UpdatePermissionsBody,
    UpdatePromptBody,
)
from app.utils.schema.response import (
    AdminAppPermissionSearch,
    AdminUserPermissionSearch,
)
from app.utils.schema.shared import BooleanResponse, IdResponse
from app.utils.types.enums import AuthScopeEnum, ClientTypeEnum, RoleEnum

logger = get_logger("api")


class AdminRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/admin", include_in_schema=False)

        self.add_api_route(
            "/status",
            self.is_admin,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(required_role=RoleEnum.APP_FIRST_PARTY))
            ],
        )
        self.add_api_route(
            "/search/app",
            self.search_apps,
            methods=["GET"],
            dependencies=[
                Depends(
                    Authentication(
                        required_role=RoleEnum.APP_FIRST_PARTY,
                        delegated_scope=AuthScopeEnum.ADMIN,
                    )
                )
            ],
        )
        self.add_api_route(
            "/search/user",
            self.search_users,
            methods=["GET"],
            dependencies=[
                Depends(
                    Authentication(
                        required_role=RoleEnum.APP_FIRST_PARTY,
                        delegated_scope=AuthScopeEnum.ADMIN,
                    )
                )
            ],
        )
        self.add_api_route(
            "/permissions/{client_type}/{id}",
            self.update_permissions,
            methods=["POST"],
            dependencies=[
                Depends(
                    Authentication(
                        required_role=RoleEnum.APP_FIRST_PARTY,
                        delegated_scope=AuthScopeEnum.ADMIN,
                    )
                )
            ],
        )
        self.add_api_route(
            "/prompts",
            self.get_prompts,
            methods=["GET"],
            dependencies=[
                Depends(
                    Authentication(
                        required_role=RoleEnum.APP_FIRST_PARTY,
                        delegated_scope=AuthScopeEnum.ADMIN,
                    )
                )
            ],
        )
        self.add_api_route(
            "/prompt/{id}",
            self.update_prompt,
            methods=["PATCH"],
            dependencies=[
                Depends(
                    Authentication(
                        required_role=RoleEnum.APP_FIRST_PARTY,
                        delegated_scope=AuthScopeEnum.ADMIN,
                    )
                )
            ],
        )
        self.add_api_route(
            "/prompt",
            self.add_prompt,
            methods=["POST"],
            dependencies=[
                Depends(
                    Authentication(
                        required_role=RoleEnum.APP_FIRST_PARTY,
                        delegated_scope=AuthScopeEnum.ADMIN,
                    )
                )
            ],
        )

    async def is_admin(self, request: Request):
        admin_service = AdminService()

        auth: AuthState = request.state.auth

        is_admin = await admin_service.is_admin(auth)
        if not is_admin:
            logger.warning("unauthenticated attempt at admin access")

        return Response(
            BooleanResponse(success=is_admin).model_dump_json(),
            status_code=status.HTTP_200_OK,
        )

    async def search_users(
        self,
        query_params: Annotated[AdminQuerySearch, Query()],
    ):
        admin_service = AdminService()

        results = await admin_service.search_users(identifier=query_params.identifier)

        return Response(
            AdminUserPermissionSearch(results=results).model_dump_json(),
            status_code=status.HTTP_200_OK,
        )

    async def search_apps(
        self,
        query_params: Annotated[AdminQuerySearch, Query()],
    ):
        admin_service = AdminService()

        results = await admin_service.search_apps(identifier=query_params.identifier)

        return Response(
            AdminAppPermissionSearch(results=results).model_dump_json(),
            status_code=status.HTTP_200_OK,
        )

    async def update_permissions(
        self,
        body: Annotated[UpdatePermissionsBody, Body()],
        client_type: ClientTypeEnum,
        id: str,
    ):
        admin_service = AdminService()

        await admin_service.update_permissions(
            id=id, client_type=client_type, body=body
        )

        return Response(
            BooleanResponse(success=True).model_dump_json(),
            status_code=status.HTTP_202_ACCEPTED,
        )

    async def get_prompts(self):
        admin_service = AdminService()

        prompts_grouped = await admin_service.get_prompts_grouped()

        return Response(
            prompts_grouped.model_dump_json(), status_code=status.HTTP_200_OK
        )

    async def update_prompt(self, body: Annotated[UpdatePromptBody, Body()], id: str):
        admin_service = AdminService()

        try:
            await admin_service.update_prompt(body=body, id=id)
            return Response(
                BooleanResponse(success=True).model_dump_json(),
                status_code=status.HTTP_202_ACCEPTED,
            )
        except Exception:
            return Response(
                BooleanResponse(success=False).model_dump_json(),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    async def add_prompt(self, body: Annotated[CreatePromptBody, Body()]):
        admin_service = AdminService()

        result = await admin_service.add_prompt(body=body)
        return Response(
            IdResponse(id=result).model_dump_json(),
            status_code=status.HTTP_202_ACCEPTED,
        )
