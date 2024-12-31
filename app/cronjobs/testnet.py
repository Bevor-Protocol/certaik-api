import logging
from typing import List
from urllib.parse import urlencode

import httpx

from app.blockchain.services.scan import fetch_contract_source_code_from_explorer
from app.utils.enums import NetworkTypeEnum, PlatformEnum
from app.utils.mappers import (
    platform_apikey_mapper,
    platform_route_mapper,
    platform_types,
)


async def fetch_recent_contracts_with_verified_source(
    platform: PlatformEnum,
) -> List[str]:
    route = platform_route_mapper[platform]
    api_key = platform_apikey_mapper[platform]

    url = f"https://api.{route}/api"
    params = {
        "module": "contract",
        "action": "getrecentverifiedcontracts",
        "apikey": api_key,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{url}?{urlencode(params)}")
            response.raise_for_status()
            data = response.json()

            contracts = data.get("result", [])
            return [
                contract.get("address")
                for contract in contracts
                if contract.get("address")
            ]

    except Exception as error:
        print(f"Error fetching recent contracts from {platform}: {error}")
        return []


async def scan_testnets_for_verified_contracts():
    platforms = platform_types[NetworkTypeEnum.TESTNET]

    tasks = []
    async with httpx.AsyncClient() as client:
        for platform in platforms:
            logging.info(f"Scanning {platform}")
            tasks.append(fetch_recent_contracts_with_verified_source(platform))
            contracts = await fetch_recent_contracts_with_verified_source(platform)
            for address in contracts:
                source_code = await fetch_contract_source_code_from_explorer(
                    client, platform, address
                )
                if source_code:
                    print(f"Verified contract found on {platform}: {address}")
                    # Process the source code as needed
