import datetime
import json
import logging
import os
import re
from typing import Optional

import httpx
import replicate
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from tortoise.exceptions import DoesNotExist

from app.api.blockchain.scan import fetch_contract_source_code_from_explorer
from app.db.models import Audit, Contract
from app.lib.markdown.gas import markdown as gas_markdown
from app.lib.markdown.security import markdown as security_markdown
from app.lib.prompts.gas import prompt as gas_prompt
from app.lib.prompts.security import prompt as security_prompt
from app.pydantic.request import EvalBody
from app.pydantic.response import EvalResponse, EvalResponseData
from app.utils.enums import AuditStatusEnum, AuditTypeEnum, ResponseStructureEnum

input_template = {
    "min_tokens": 512,
    "max_tokens": 3000,
    "system_prompt": (
        "You are a helpful assistant, specializing in smart contract auditing"
    ),
    "prompt_template": """
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>

    {system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>

    {prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
    """,
}


replicate_client = replicate.Client(api_token=os.getenv("REPLICATE_API_KEY"))


def sanitize_data(raw_data: str, audit_type: AuditTypeEnum, as_markdown: bool):
    # sanitizing backslashes/escapes for code blocks
    pattern = r"<<(.*?)>>"
    raw_data = re.sub(pattern, "`", raw_data)

    parsed = json.loads(raw_data)

    if as_markdown:
        parsed = parse_branded_markdown(audit_type=audit_type, findings=parsed)

    return parsed


def parse_branded_markdown(audit_type: AuditTypeEnum, findings: dict):
    result = gas_markdown if audit_type == AuditTypeEnum.GAS else security_markdown

    formatter = {
        "project_name": findings["audit_summary"].get("project_name", "Unknown"),
        "address": "Unknown",
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "introduction": findings["introduction"],
        "scope": findings["scope"],
        "conclusion": findings["conclusion"],
    }

    pattern = r"<<(.*?)>>"

    rec_string = ""
    for rec in findings["recommendations"]:
        rec_string += f"- {rec}\n"
    formatter["recommendations"] = rec_string.strip()

    for k, v in findings["findings"].items():
        key = f"findings_{k}"
        finding_str = ""
        if not v:
            finding_str = "None Identified"
        else:
            for finding in v:
                finding = re.sub(pattern, r"`\1`", finding)
                finding_str += f"- {finding}\n"

        formatter[key] = finding_str.strip()

    return result.format(**formatter)


async def process_evaluation(user: Optional[str], data: EvalBody) -> JSONResponse:
    contract_code = data.contract_code
    contract_address = data.contract_address
    contract_network = data.contract_network
    audit_type = data.audit_type
    webhook_url = data.webhook_url

    if contract_address:
        contract: Optional[Contract] = await Contract.first(
            contract_address=contract_address, contract_network=contract_network
        )
        if contract:
            contract_code = contract.contract_code

    if not contract_code:
        async with httpx.AsyncClient() as client:
            response = await fetch_contract_source_code_from_explorer(
                client, contract_network, contract_address
            )
            if not response:
                raise HTTPException(
                    status_code=404,
                    detail="No source code found for the given address on any platform",
                )
            contract = response
        new_contract_instance = Contract(
            contract_address=contract_address,
            contract_network=contract_network,
            contract_code=response,
        )
        await new_contract_instance.save()
    else:
        contract = contract_code

    prompt = gas_prompt if audit_type == AuditTypeEnum.GAS else security_prompt

    if not contract or not prompt:
        raise HTTPException(status_code=400, detail="Must provide input")

    audit_prompt = prompt.replace("<{prompt}>", contract)
    input_data = {**input_template, "prompt": audit_prompt}

    internal_webhook_url = os.getenv("API_URL")

    webhook_url_pass = f"{internal_webhook_url}/ai/eval/webhook"
    if webhook_url:
        webhook_url_pass += f"?chained_call={webhook_url}"

    response = await replicate_client.predictions.async_create(
        model="meta/meta-llama-3-70b-instruct",
        input=input_data,
        webhook=webhook_url_pass,
        webhook_events_filter=["completed"],
    )

    audit = await Audit.create(
        job_id=response.id,
        contract_address=contract_address,
        contract_network=network,
        contract_code=contract_code,
        audit_type=audit_type,
    )

    return {"job_id": str(audit.id)}


async def get_eval(id: str, response_type: ResponseStructureEnum) -> EvalResponse:

    try:
        audit = await Audit.get(id=id)
    except DoesNotExist as err:
        logging.error(err)
        response = EvalResponse(
            success=False, exists=False, error="no record of this evaluation exists"
        )
        return response

    response = EvalResponse(
        success=True,
        exists=True,
    )

    data = {
        "id": str(audit.id),
        "response_type": response_type,
        "contract_address": audit.contract_address,
        "contract_code": audit.contract_code,
        "contract_network": audit.contract_network,
        "status": audit.results_status,
    }

    if audit.results_status == AuditStatusEnum.SUCCESS:
        if response_type == ResponseStructureEnum.RAW:
            data["result"] = audit.results_raw_output
        else:
            try:
                data["result"] = sanitize_data(
                    raw_data=audit.results_raw_output,
                    audit_type=audit.audit_type,
                    as_markdown=response_type == ResponseStructureEnum.MARKDOWN,
                )
            except json.JSONDecodeError as err:
                logging.error(f"Unable to parse the output correctly: {err}")

    response.result = EvalResponseData(**data)

    return response