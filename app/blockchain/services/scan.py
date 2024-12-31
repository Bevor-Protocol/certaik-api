import json
import logging
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from app.cache import redis_client
from app.utils.enums import NetworkTypeEnum, PlatformEnum
from app.utils.mappers import (
    platform_explorer_apikey_mapper,
    platform_explorer_mapper,
    platform_types,
)

logging.basicConfig(level=logging.INFO)


async def fetch_contract_source_code_from_explorer(
    client: httpx.AsyncClient, platform: PlatformEnum, address: str
) -> Optional[str]:
    platform_route = platform_explorer_mapper[platform]
    api_key = platform_explorer_apikey_mapper[platform]

    url = f"https://{platform_route}/api"
    params = {
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
        "apikey": api_key,
    }

    try:
        response = await client.get(f"{url}?{urlencode(params)}")
        response.raise_for_status()
        data = response.json()

        result = data.get("result", [])
        if result and isinstance(result, list) and len(result) > 0:
            source_code = result[0].get("SourceCode")
            if source_code:
                return source_code
        raise Exception("No source code found")

    except Exception as error:
        print(
            f"Error fetching contract source code from {platform} "
            f"for address {address}: {error}"
        )
        return None


async def fetch_contract_source_code(address: str):
    if not address:
        raise HTTPException(status_code=400, detail="Address parameter is required")

    KEY = f"scan|{address}"
    res = redis_client.get(KEY)
    if res:
        data = json.loads(res)
        logging.info(f"CACHE KEY HIT {KEY}")
        return data
    try:
        platforms = platform_types[NetworkTypeEnum.MAINNET]

        async with httpx.AsyncClient() as client:
            for platform in platforms:
                # we want this to be blocking so we can early exit
                source_code = await fetch_contract_source_code_from_explorer(
                    client, platform, address
                )
                if source_code:
                    data = {"platform": platform.value, "source_code": source_code}
                    redis_client.set(KEY, json.dumps(data))
                    return data

        raise HTTPException(
            status_code=404,
            detail="No source code found for the given address on any platform",
        )
    except HTTPException as http_error:
        # don't want to lose granularity by pass to next statement
        raise http_error
    except Exception as error:
        logging.error(error)
        raise HTTPException(status_code=500, detail=str(error))
