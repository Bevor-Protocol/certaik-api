from fastapi import APIRouter, Depends

from app.api.blockchain.service import BlockchainService
from app.api.dependencies import Authentication
from app.utils.types.enums import RoleEnum


class BlockchainRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/blockchain", include_in_schema=False)

        self.add_api_route(
            "/gas",
            self.get_gas,
            methods=["GET"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
        )

    async def get_gas(self):
        blockchain_service = BlockchainService()
        return await blockchain_service.get_gas()
