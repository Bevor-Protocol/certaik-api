import datetime
import json
import logging
import os
import re

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from tortoise.exceptions import DoesNotExist

from app.api.ai.pipeline import LlmPipeline
from app.api.blockchain.scan import get_or_create_contract
from app.api.middleware.auth import UserDict
from app.db.models import Audit
from app.lib.v1.markdown.gas import markdown as gas_markdown
from app.lib.v1.markdown.security import markdown as security_markdown

# from app.lib.prompts.gas import prompt as gas_prompt
# from app.lib.prompts.security import prompt as security_prompt
from app.pydantic.request import EvalBody
from app.pydantic.response import EvalResponse, EvalResponseData
from app.utils.enums import AuditStatusEnum, AuditTypeEnum, ResponseStructureEnum

input_template = {
    "min_tokens": 512,
    "max_tokens": 1500,
    "system_prompt": (
        "You are a helpful assistant, specializing in smart contract auditing"
    ),
    "prompt_template": """
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>

    {system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>

    {prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
    """,
}


def sanitize_data(raw_data: str, audit_type: AuditTypeEnum, as_markdown: bool):
    # sanitizing backslashes/escapes for code blocks
    pattern = r"<<(.*?)>>"
    raw_data = re.sub(pattern, r"`\1`", raw_data)

    # corrects for occassional leading non-json text...
    pattern = r"\{.*\}"
    match = re.search(pattern, raw_data, re.DOTALL)
    if match:
        raw_data = match.group(0)

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


async def process_evaluation(user: UserDict, data: EvalBody) -> JSONResponse:
    contract_code = data.contract_code
    contract_address = data.contract_address
    contract_network = data.contract_network
    audit_type = data.audit_type
    webhook_url = data.webhook_url

    contract = await get_or_create_contract(
        contract_code=contract_code,
        contract_address=contract_address,
        contract_network=contract_network,
    )

    if not contract:
        raise HTTPException(
            status_code=404,
            detail=(
                "no verified source code found for the contract information provided"
            ),
        )

    # prompt = gas_prompt if audit_type == AuditTypeEnum.GAS else security_prompt

    # audit_prompt = prompt.replace("<{prompt}>", contract_code)

    # internal_webhook_url = os.getenv("API_URL")

    # webhook_url_pass = f"{internal_webhook_url}/ai/eval/webhook"
    # if webhook_url:
    #     webhook_url_pass += f"?chained_call={webhook_url}"

    # candidate_results = []
    # for _ in range(3):
    #     candidate_results.append(
    #         replicate_client.predictions.create(
    #             model="meta/meta-llama-3-70b-instruct",
    #             input={**input_template, "prompt": audit_prompt, "temperature": 0.8},
    #         )
    #     )

    # logging.info(candidate_results[0].output)

    # judge_prompt = (
    #     audit_prompt
    #     + "\n\nHere are some candidate findings, please review and critique them carefully:"
    # )
    # for i, candidate in enumerate(candidate_results):
    #     output = "".join(candidate.output).strip()
    #     judge_prompt += f"\nFinding {i+1}:\n{output}"

    # judge = await replicate_client.predictions.async_create(
    #     model="meta/meta-llama-3-70b-instruct",
    #     input={**input_template, "prompt": judge_prompt, "temperature": 0.2},
    # )

    # judge_output = "".join(judge.output).strip()

    # final_prompt = (
    #     judge_prompt
    #     + f"\n\nHere is meaningful critique around the findings, use it to infer the best possible result, and be certain to return the JSON output structure that was outlined\n\n{judge_output}"
    # )

    # finalized = await replicate_client.predictions.async_create(
    #     model="meta/meta-llama-3-70b-instruct",
    #     input={**input_template, "prompt": final_prompt, "temperature": 0.2},
    # )

    pipeline = LlmPipeline(input=contract_code)
    await pipeline.generate_candidates()
    logging.info(f"CANDIDATES:\n\n{pipeline.candidate_prompt}")
    await pipeline.generate_judgement()
    logging.info(f"JUDGEMENT:\n\n{pipeline.judgement_prompt}")
    response = await pipeline.generate_report()

    logging.info(response)
    return {"job_id": "ok"}

    audit = await Audit.create(
        job_id=response.id,
        contract=contract,
        app=user["app"],
        user=user["user"],
        audit_type=audit_type,
        prompt_version=1,
        model="meta/meta-llama-3-70b-instruct",
    )

    return {"job_id": str(audit.id)}


async def get_eval(id: str, response_type: ResponseStructureEnum) -> EvalResponse:

    try:
        audit = await Audit.get(id=id).select_related("contract")
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
        "contract_address": audit.contract.address,
        "contract_code": audit.contract.raw_code,
        "contract_network": audit.contract.network,
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
                logging.error(
                    f"Unable to parse the output correctly for {str(audit.id)}: {err}"
                )

    response.result = EvalResponseData(**data)

    return response
