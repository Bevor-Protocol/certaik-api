import logging

import httpx
from fastapi import APIRouter, HTTPException

from app.utils.enums import PlatformEnum

from .services.gas import fetch_gas
from .services.scan import (
    fetch_contract_source_code,
    fetch_contract_source_code_from_explorer,
)

router = APIRouter()


@router.get("/scan/{address}")
async def scan_contract(address: str):
    return await fetch_contract_source_code(address)


@router.get("/scan/{address}/{network}")
async def scan_contract_on_network(address: str, network: str):
    try:
        platform = PlatformEnum[network.upper()]
        async with httpx.AsyncClient() as client:
            response = await fetch_contract_source_code_from_explorer(
                client, platform, address
            )
            if not response:
                raise HTTPException(
                    status_code=404,
                    detail="No source code found for the given address on any platform",
                )

            return response
    except KeyError:
        raise HTTPException(status_code=500, detail="invalid network")
    except Exception as error:
        logging.error(error)
        raise HTTPException(status_code=500, detail=str(error))


@router.get("/gas")
async def get_gas():
    return await fetch_gas()
