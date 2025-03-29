from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from tortoise.exceptions import DoesNotExist

from app.api.contract.service import ContractService
from app.api.dependencies import AuthenticationWithoutDelegation, RequireCredits
from app.api.pricing.service import StaticAnalysis
from app.db.models import Transaction, User
from app.utils.constants.openapi_tags import CONTRACT_TAG
from app.utils.schema.dependencies import AuthState
from app.utils.schema.request import ContractScanBody
from app.utils.types.enums import RoleEnum, TransactionTypeEnum

from .openapi import GET_CONTRACT, GET_OR_CREATE_CONTRACT


class ContractRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/contract", tags=[CONTRACT_TAG])

        self.add_api_route(
            "",
            self.upload_contract,
            methods=["POST"],
            dependencies=[
                Depends(AuthenticationWithoutDelegation(required_role=RoleEnum.USER))
            ],
            **GET_OR_CREATE_CONTRACT,
        )
        self.add_api_route(
            "/{id}",
            self.get_contract,
            methods=["GET"],
            dependencies=[
                Depends(AuthenticationWithoutDelegation(required_role=RoleEnum.USER))
            ],
            **GET_CONTRACT,
        )
        self.add_api_route(
            "/token/static",
            self.process_token,
            methods=["POST"],
            dependencies=[
                Depends(AuthenticationWithoutDelegation(required_role=RoleEnum.USER)),
                Depends(RequireCredits()),
            ],
            # **ANALYZE_TOKEN,
            include_in_schema=False,
        )

    async def upload_contract(self, body: Annotated[ContractScanBody, Body()]):
        contract_service = ContractService()
        response = await contract_service.fetch_from_source(
            address=body.address, network=body.network, code=body.code
        )

        return Response(
            response.model_dump_json(), status_code=status.HTTP_202_ACCEPTED
        )

    async def get_contract(self, id: str):
        contract_service = ContractService()

        try:
            response = await contract_service.get(id)
            return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)
        except DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="this contract does not exist",
            )

    async def process_token(
        self,
        request: Request,
        body: Annotated[ContractScanBody, Body()],
    ):
        contract_service = ContractService()
        static_pricing = StaticAnalysis()
        auth: AuthState = request.state.auth

        response = await contract_service.process_static_eval_token(body)

        if auth.consumes_credits:
            user = await User.get(id=auth.credit_consumer_user_id)
            price = static_pricing.get_cost()
            user.used_credits += price
            await user.save()
            await Transaction.create(
                app_id=auth.app_id,
                user_id=auth.user_id,
                type=TransactionTypeEnum.SPEND,
                amount=price,
            )

        return Response(
            response.model_dump_json(), status_code=status.HTTP_202_ACCEPTED
        )
