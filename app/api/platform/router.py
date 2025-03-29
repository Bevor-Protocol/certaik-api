from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import AuthenticationWithoutDelegation
from app.api.pricing.service import Usage
from app.utils.constants.openapi_tags import PLATFORM_TAG
from app.utils.schema.response import GetCostEstimateResponse
from app.utils.types.enums import RoleEnum

from .openapi import GET_COST_ESTIMATE


class PlatformRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/platform", tags=[PLATFORM_TAG])

        self.add_api_route(
            "/cost-estimate",
            self.get_credit_estimate,
            methods=["GET"],
            dependencies=[
                Depends(AuthenticationWithoutDelegation(required_role=RoleEnum.USER))
            ],
            **GET_COST_ESTIMATE
        )

    async def get_credit_estimate(self):
        usage = Usage()
        estimate = usage.estimate_pricing()
        response = GetCostEstimateResponse(credits=estimate)
        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)
