import json
import logging
import os

import httpx

from app.utils.clients.explorer import ExplorerClient
from app.utils.clients.web3 import Web3Client
from app.utils.types.enums import NetworkEnum
from app.utils.types.errors import NoSourceCodeError


class BlockchainService:

    async def get_gas(self) -> dict:
        explorer_client = ExplorerClient()

        async with httpx.AsyncClient() as client:
            response = await explorer_client.get_gas(
                client=client, network=NetworkEnum.ETH
            )
            response.raise_for_status()

            data = response.json()
            return data

    def __parse_source_code(self, scan_results: list[dict]):
        """
        Etherscan response object can be a plaintext response,
        or a object of dependencies.
        Extract source code of contract of interest.
        """

        if not scan_results:
            return

        scan_result = scan_results[0]
        source_code = scan_result.get("SourceCode")

        if not source_code:
            # Will handle empty, or plaintext responses.
            return source_code

        contract_name = scan_result["ContractName"] + ".sol"

        source_code = json.loads(
            source_code.strip(" '").replace("{{", "{").replace("}}", "}")
        )

        for k, v in source_code["sources"].items():
            if contract_name in k:
                return v["content"]

        raise NoSourceCodeError("Unable to parse source code")

    async def fetch_contract_source_code_from_explorer(
        self, client: httpx.AsyncClient, address: str, network: NetworkEnum
    ) -> dict:
        explorer_client = ExplorerClient()

        logging.info(f"SCANNING {network} for address {address}")

        obj = {
            "network": network,
            "address": address,
            "has_source_code": False,
            "found": False,
            "source_code": None,
        }

        try:
            response = await explorer_client.get_source_code(
                client=client, network=network, address=address
            )
            response.raise_for_status()
            data = response.json()

            result = data.get("result")
            if result and isinstance(result, list) and len(result) > 0:
                obj["found"] = True
                source_code = self.__parse_source_code(result)
                if source_code:
                    obj["has_source_code"] = True
                    obj["source_code"] = source_code
            raise NoSourceCodeError()
        except NoSourceCodeError:
            obj["found"] = True
        except Exception:
            pass
        finally:
            return obj

    async def get_credits(self, address: str) -> float:
        web3_client = Web3Client()
        provider = web3_client.get_deployed_provider()

        env = os.getenv("RAILWAY_ENVIRONMENT_NAME", "development")
        if env == "production":
            contract_address = provider.to_checksum_address(
                "0x1bdEEe6376572F1CAE454dC68a936Af56A803e96"
            )
        elif env == "staging":
            contract_address = provider.to_checksum_address(
                "0xbc14A36c59154971A8Eb431031729Af39f97eEd1"
            )
        else:
            contract_address = provider.to_checksum_address(
                "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512"
            )

        user_address = provider.to_checksum_address(address)

        abi = [
            {
                "inputs": [{"type": "address"}],
                "name": "apiCredits",
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            }
        ]

        contract = provider.eth.contract(address=contract_address, abi=abi)

        # Call apiCredits mapping to get credits for the address
        credits_raw = await contract.functions.apiCredits(user_address).call()
        credits = credits_raw / 10**18

        return credits
