import logging

import httpx
from fastapi import APIRouter, HTTPException

from app.api.blockchain.gas import fetch_gas
from app.api.blockchain.scan import (
    fetch_contract_source_code,
    fetch_contract_source_code_from_explorer,
)
from app.utils.enums import PlatformEnum


class BlockchainRouter:
    def __init__(self):
        super().__init__()
        self.router = APIRouter(prefix="/blockchain", tags=["blockchain"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "/scan/{address}", self.scan_contract, methods=["GET"]
        )
        self.router.add_api_route(
            "/scan/{address}/{network}", self.scan_contract_on_network, methods=["GET"]
        )
        self.router.add_api_route("/gas", self.get_gas, methods=["GET"])

    async def scan_contract(self, address: str):
        return await fetch_contract_source_code(address)

    async def scan_contract_on_network(self, address: str, network: str):
        try:
            platform = PlatformEnum[network.upper()]
            async with httpx.AsyncClient() as client:
                response = await fetch_contract_source_code_from_explorer(
                    client, platform, address
                )
                if not response:
                    raise HTTPException(
                        status_code=404,
                        detail="No source code found for the given address",
                    )

                return response
        except KeyError:
            raise HTTPException(status_code=500, detail="invalid network")
        except Exception as error:
            logging.error(error)
            raise HTTPException(status_code=500, detail=str(error))

    async def get_gas(self):
        return await fetch_gas()