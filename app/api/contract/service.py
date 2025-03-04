import asyncio
import hashlib
from typing import Optional

import httpx
from fastapi import HTTPException, status
from solidity_parser import parser

from app.api.blockchain.service import BlockchainService
from app.db.models import Contract
from app.utils.helpers.mappers import networks_by_type
from app.utils.helpers.model_parser import cast_contract_with_code
from app.utils.schema.contract import ContractWithCodePydantic
from app.utils.schema.request import ContractScanBody
from app.utils.schema.response import StaticAnalysisTokenResult, UploadContractResponse
from app.utils.types.enums import ContractMethodEnum, NetworkEnum, NetworkTypeEnum


class ContractService:

    def __init__(
        self,
        allow_testnet: bool = False,
    ):
        self.allow_testnet = allow_testnet

    async def __get_contract_candidates(
        self,
        code: Optional[str],
        address: Optional[str],
        network: Optional[NetworkEnum],
    ) -> list[Contract]:
        filter_obj = {"is_available": True, "raw_code__isnull": False}

        if address:
            filter_obj["address"] = address
            if network:
                filter_obj["network"] = network
            contracts = await Contract.filter(**filter_obj)
        else:
            hashed_content = hashlib.sha256(code.encode()).hexdigest()
            filter_obj["hash_code"] = hashed_content
            if network:
                filter_obj["network"] = network
            contracts = await Contract.filter(hash_code=hashed_content)

        return contracts or []

    async def __get_or_create_contract(
        self,
        code: Optional[str],
        address: Optional[str],
        network: Optional[NetworkEnum],
    ) -> list[Contract]:
        """
        A contract's source code can be queried in many ways
        1. The source code alone was used -> via upload
        2. Only the address was provided -> via scan
        3. The address and network were provided -> via scan

        If method of SCAN was used, it's possible that the contract is not verified,
        and we aren't able to fetch the source code.

        Steps:
        - code Contract record, if available
        - if we had previously managed to fetch the source code, use it and return
        - if the network was provided, search it. Otherwise search all networks
        - if source code was found, create a new Contract record, unless we already had
            a scan for this address + network and weren't able to fetch source code,
            then update it.
        """

        contracts = await self.__get_contract_candidates(
            code=code, address=address, network=network
        )

        # More granular logic below to still scan, but not update instead of create.
        if contracts:
            return contracts

        if code:
            contract = await Contract.create(
                method=ContractMethodEnum.UPLOAD,
                network=network,
                raw_code=code,
            )
            return [contract]

        if network:
            networks_scan = [network]
        else:
            networks_scan = networks_by_type[NetworkTypeEnum.MAINNET]
            networks_scan = [NetworkEnum.ETH]
            if self.allow_testnet:
                networks_scan += networks_by_type[NetworkTypeEnum.TESTNET]

        # Rather than calling these sequentially and breaking, we'll call them all.
        # For example, USDC contract on ETH mainnet is an address on BASE, so it early
        # exits without finding source code...
        tasks = []
        blockchain_service = BlockchainService()
        async with httpx.AsyncClient() as client:
            for network in networks_scan:
                tasks.append(
                    asyncio.create_task(
                        blockchain_service.fetch_contract_source_code_from_explorer(
                            client=client, address=address, network=network
                        )
                    )
                )

            results: list[dict] = await asyncio.gather(*tasks)

        # only return those with source code.
        contracts_return: list[Contract] = []
        for result in results:
            if result["found"]:
                contract = Contract(
                    method=ContractMethodEnum.SCAN,
                    address=address,
                    is_available=result["has_source_code"],
                    network=result["network"],
                )
                if result["has_source_code"]:
                    contract.raw_code = result["source_code"]
                    await contract.save()
                    contracts_return.append(contract)
                else:
                    await contract.save()

                # contract.n_retries = contract.n_retries + 1
                # contract.next_attempt = datetime.datetime.now()

        return contracts_return

    async def fetch_from_source(
        self,
        code: Optional[str] = None,
        address: Optional[str] = None,
        network: Optional[NetworkEnum] = None,
    ) -> UploadContractResponse:

        if not code and not address:
            raise ValueError("Either contract code or address must be provided")

        contracts = await self.__get_or_create_contract(
            code=code, address=address, network=network
        )

        first_candidate = next(filter(lambda x: x.is_available, contracts), None)
        if first_candidate:
            first_candidate = cast_contract_with_code(first_candidate)

        return UploadContractResponse(
            exact_match=len(contracts) == 1,
            exists=first_candidate is not None,
            contract=first_candidate,
        )

    async def get(self, id: str) -> ContractWithCodePydantic:

        contract = await Contract.get(id=id)

        return cast_contract_with_code(contract)

    def analyze_contract(self, ast: dict) -> StaticAnalysisTokenResult:
        """
        Analyzes contract AST for various security and functionality characteristics.
        Returns a dictionary of analysis results.
        """
        results = {
            "is_mintable": {"internal_mint": False, "public_mint": False},
            "is_honeypot": False,
            "can_steal_fees": False,
            "can_self_destruct": False,
            "has_proxy_functions": False,
            "has_allowlist": False,
            "has_blocklist": False,
            "can_terminate_transactions": False,
        }

        def traverse_nodes(nodes):
            for node in nodes:
                if node.get("type") == "ContractDefinition":
                    self._analyze_contract_nodes(node.get("subNodes", []), results)
                elif isinstance(node, dict):
                    for value in node.values():
                        if isinstance(value, list):
                            traverse_nodes(value)

        traverse_nodes(ast.get("children", []))

        # Final mintable check combining internal and public results
        results["is_mintable"] = (
            results["is_mintable"]["internal_mint"]
            and results["is_mintable"]["public_mint"]
        )

        return StaticAnalysisTokenResult(**results)

    def _analyze_contract_nodes(self, nodes, results):
        for node in nodes:
            if node.get("type") == "FunctionDefinition":
                name = node.get("name", "").lower()
                visibility = node.get("visibility", "")
                body = str(node.get("body", {}))

                # Mintable checks
                if name == "mint" and visibility in ["public", "external"]:
                    results["is_mintable"]["public_mint"] = True
                elif name == "_mint":
                    results["is_mintable"]["internal_mint"] = True
                elif visibility in ["public", "external"] and "_mint" in body:
                    results["is_mintable"]["public_mint"] = True

                # Honeypot checks
                if ("require" in body and "transfer" in body) or (
                    "revert" in body and "transfer" in body
                ):
                    results["is_honeypot"] = True

                # Fee stealing checks
                if any(
                    x in name for x in ["withdraw", "claim", "collect"]
                ) and visibility in ["public", "external"]:
                    results["can_steal_fees"] = True

                # Self-destruct checks
                if "selfdestruct" in body or "suicide" in body:
                    results["can_self_destruct"] = True

                # Proxy function checks
                if "delegatecall" in body or "callcode" in body:
                    results["has_proxy_functions"] = True

                # Transaction termination checks
                if "assert" in body or "revert" in body:
                    results["can_terminate_transactions"] = True

            # Check variable names for allow/blocklists
            name = str(node.get("name", "")).lower()
            if any(x in name for x in ["whitelist", "allowlist", "allowed"]):
                results["has_allowlist"] = True
            if any(x in name for x in ["blacklist", "blocklist", "banned"]):
                results["has_blocklist"] = True

    def _generate_ast(self, source_code: str):
        try:
            ast = parser.parse(source_code)
            print("AST:", ast)
            return ast
        except Exception as e:
            print("Error parsing source code:", e)
            raise e

    async def process_static_eval_token(
        self, body: ContractScanBody
    ) -> StaticAnalysisTokenResult:
        contract_service = ContractService()

        contract_info = await contract_service.fetch_from_source(
            code=body.code, address=body.address, network=body.network
        )

        if not contract_info.exists:
            raise HTTPException(
                detail="no source code found for this address",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        ast = self._generate_ast(contract_info.contract.code)
        analysis = self.analyze_contract(ast)

        return analysis
