from typing import Annotated

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from tortoise.exceptions import DoesNotExist

from app.api.audit.service import AuditService
from app.api.dependencies import Authentication, RequireCredits
from app.utils.constants.openapi_tags import AUDIT_TAG
from app.utils.schema.request import EvalBody, FeedbackBody, FilterParams
from app.utils.schema.response import GetAuditStatusResponse
from app.utils.schema.shared import BooleanResponse
from app.utils.types.enums import RoleEnum

from .openapi import (
    CREATE_AUDIT,
    GET_AUDIT,
    GET_AUDIT_STATUS,
    GET_AUDITS,
    SUBMIT_FEEDBACK,
)


class AuditRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/audit", tags=[AUDIT_TAG])

        self.add_api_route(
            "",
            self.create_audit,
            methods=["POST"],
            dependencies=[
                Depends(Authentication(required_role=RoleEnum.USER)),
                Depends(RequireCredits()),
            ],
            **CREATE_AUDIT,
        )
        self.add_api_route(
            "/list",
            self.list_audits,
            methods=["GET"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
            **GET_AUDITS,
        )
        self.add_api_route(
            "/{id}",
            self.get_audit,
            methods=["GET"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
            **GET_AUDIT,
        )
        self.add_api_route(
            "/{id}/status",
            self.get_audit_status,
            methods=["GET"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
            **GET_AUDIT_STATUS,
        )
        self.add_api_route(
            "/{id}/feedback",
            self.submit_feedback,
            methods=["POST"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
            **SUBMIT_FEEDBACK,
        )

    async def create_audit(
        self,
        request: Request,
        body: Annotated[EvalBody, Body()],
    ):
        audit_service = AuditService()
        response = await audit_service.process_evaluation(
            auth=request.state.auth, data=body
        )
        return Response(response.model_dump_json(), status_code=status.HTTP_201_CREATED)

    async def list_audits(
        self,
        request: Request,
        query_params: Annotated[FilterParams, Query()],
    ):
        # rate_limit(request=request, user=user)
        audit_service = AuditService()
        response = await audit_service.get_audits(
            auth=request.state.auth,
            query=query_params,
        )

        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)

    async def get_audit(self, request: Request, id: str):
        audit_service = AuditService()

        try:
            audit = await audit_service.get_audit(auth=request.state.auth, id=id)
            return Response(audit.model_dump_json(), status_code=status.HTTP_200_OK)
        except DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="this audit does not exist under these credentials",
            )

    async def get_audit_status(
        self, request: Request, id: str
    ) -> GetAuditStatusResponse:
        audit_service = AuditService()

        try:
            response = await audit_service.get_status(auth=request.state.auth, id=id)
            return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)
        except DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="this audit does not exist under these credentials",
            )

    async def submit_feedback(
        self, request: Request, body: Annotated[FeedbackBody, Body()], id: str
    ):
        audit_service = AuditService()
        response = await audit_service.submit_feedback(
            data=body, auth=request.state.auth, id=id
        )
        return Response(
            BooleanResponse(success=response).model_dump_json(),
            status_code=status.HTTP_201_CREATED,
        )
