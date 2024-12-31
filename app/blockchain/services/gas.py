from urllib.parse import urlencode

import httpx
from fastapi.responses import JSONResponse

from app.utils.enums import PlatformEnum
from app.utils.mappers import platform_explorer_apikey_mapper, platform_explorer_mapper


async def fetch_gas():
    api_key = platform_explorer_apikey_mapper[PlatformEnum.ETH]
    route = platform_explorer_mapper[PlatformEnum.ETH]
    url = f"https://{route}/api"
    params = {
        "module": "gastracker",
        "action": "gasoracle",
        "apikey": api_key,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{url}?{urlencode(params)}")
            response.raise_for_status()

            data = response.json()
            return JSONResponse(data, status_code=200)
    except httpx.RequestError as e:
        return JSONResponse(
            {"error": f"An error occurred while requesting {e.request.url!r}."}
        )
    except httpx.HTTPStatusError as e:
        error_message = ""
        if e.response.text:
            error_message = e.response.text
        else:
            error_message = (
                f"Error response {e.response.status_code}"
                f"while requesting {e.request.url!r}."
            )
        return JSONResponse({"error": error_message})
