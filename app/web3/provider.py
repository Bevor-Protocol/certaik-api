import os

from web3 import Web3

from app.utils.enums import PlatformEnum
from app.utils.mappers import platform_rpc_mapper


def get_provider(platform: PlatformEnum) -> Web3:
    rpc_url = platform_rpc_mapper[platform]
    api_key = os.getenv("ALCHEMY_API_KEY")
    url = f"https://{rpc_url}/v2/{api_key}"

    return Web3(Web3.HTTPProvider(url))
