from typing import Annotated

from fastapi import APIRouter, Body, Depends, Response, status

from app.api.blockchain.service import BlockchainService
from app.api.contract.service import ContractService
from app.api.dependencies import Authentication
from app.utils.schema.request import ContractScanBody
from app.utils.types.enums import AuthRequestScopeEnum


class BlockchainRouter:
    def __init__(self):
        super().__init__()
        self.router = APIRouter(prefix="/blockchain", include_in_schema=False)
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "/gas",
            self.get_gas,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
        )

    async def upload_contract(self, body: Annotated[ContractScanBody, Body()]):
        contract_service = ContractService()
        response = await contract_service.fetch_from_source(
            address=body.address, network=body.network, code=body.code
        )

        return Response(
            response.model_dump_json(), status_code=status.HTTP_202_ACCEPTED
        )

    async def get_gas(self):
        blockchain_service = BlockchainService()
        return await blockchain_service.get_gas()
