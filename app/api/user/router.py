from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from tortoise.exceptions import DoesNotExist

from app.api.dependencies import Authentication, AuthenticationWithoutDelegation
from app.api.user.service import UserService
from app.utils.constants.openapi_tags import USER_TAG
from app.utils.schema.request import UserUpsertBody
from app.utils.schema.response import IdResponse
from app.utils.types.enums import RoleEnum

from .openapi import GET_OR_CREATE_USER, GET_USER_INFO


class UserRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/user", tags=[USER_TAG])

        self.add_api_route(
            "",
            self.get_or_create_user,
            methods=["POST"],
            dependencies=[
                Depends(AuthenticationWithoutDelegation(required_role=RoleEnum.APP))
            ],
            **GET_OR_CREATE_USER,
        )
        self.add_api_route(
            "/info",
            self.get_user_info,
            methods=["GET"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
            **GET_USER_INFO,
        )

    async def get_or_create_user(self, body: Annotated[UserUpsertBody, Body()]):
        # Users are created through apps. A user is denoted by their address,
        # but might have different app owners that they were created through.
        user_service = UserService()

        result = await user_service.get_or_create(body.address)
        response = IdResponse(id=result.id)

        return Response(
            response.model_dump_json(), status_code=status.HTTP_202_ACCEPTED
        )

    async def get_user_info(self, request: Request):
        user_service = UserService()
        try:
            user_info = await user_service.get_info(request.state.auth)
            return Response(user_info.model_dump_json(), status_code=status.HTTP_200_OK)
        except DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="this user does not exist under these credentials",
            )
