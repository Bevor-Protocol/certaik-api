import json
import logging
import re

from arq import create_pool
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from tortoise.exceptions import DoesNotExist

from app.api.middleware.auth import UserDict
from app.config import redis_settings
from app.db.models import Audit, Contract
from app.lib.v1.markdown.gas import markdown as gas_markdown
from app.lib.v1.markdown.security import markdown as security_markdown

# from app.lib.prompts.gas import prompt as gas_prompt
# from app.lib.prompts.security import prompt as security_prompt
from app.pydantic.request import EvalBody
from app.pydantic.response import EvalResponse, EvalResponseData
from app.utils.enums import (
    AuditProjectTypeEnum,
    AuditStatusEnum,
    AuditTypeEnum,
    ResponseStructureEnum,
)

# from app.worker import process_eval


class EvalService:

    def __init__(self):
        pass

    def sanitize_data(self, audit: Audit, as_markdown: bool):
        # sanitizing backslashes/escapes for code blocks
        pattern = r"<<(.*?)>>"

        # this parsing should not be required, but we'll include it for safety
        raw_data = re.sub(pattern, r"`\1`", audit.raw_output)

        # corrects for occassional leading non-json text...
        pattern = r"\{.*\}"
        match = re.search(pattern, raw_data, re.DOTALL)
        if match:
            raw_data = match.group(0)

        parsed = json.loads(raw_data)

        if as_markdown:
            parsed = self.parse_branded_markdown(audit=audit, findings=parsed)

        return parsed

    def parse_branded_markdown(self, audit: Audit, findings: dict):
        # See if i can cast it back to the expected Pydantic struct.
        markdown = (
            gas_markdown if audit.audit_type == AuditTypeEnum.GAS else security_markdown
        )
        result = markdown

        formatter = {
            "address": audit.contract.address,
            "date": audit.created_at.strftime("%Y-%m-%d"),
            "introduction": findings["introduction"],
            "scope": findings["scope"],
            "conclusion": findings["conclusion"],
        }

        pattern = r"<<(.*?)>>"

        for k, v in findings["findings"].items():
            key = f"findings_{k}"
            finding_str = ""
            if not v:
                finding_str = "None Identified"
            else:
                for finding in v:
                    name = re.sub(pattern, r"`\1`", finding["name"])
                    explanation = re.sub(pattern, r"`\1`", finding["explanation"])
                    recommendation = re.sub(pattern, r"`\1`", finding["recommendation"])
                    reference = re.sub(pattern, r"`\1`", finding["reference"])

                    finding_str += f"**{name}**\n"
                    finding_str += f"- **Explanation**: {explanation}\n"
                    finding_str += f"- **Recommendation**: {recommendation}\n"
                    finding_str += f"- **Code Reference**: {reference}\n\n"

            formatter[key] = finding_str.strip()

        return result.format(**formatter)

    async def add_agent_security_score(
        self, audit: Audit, security_score: float
    ) -> None:
        """
        Updates an audit record with agent security score and project type

        Args:
            audit: The Audit model instance to update
            security_score: The security score to set
        """
        audit.project_type = AuditProjectTypeEnum.AGENT
        audit.security_score = security_score
        await audit.save()

    async def process_evaluation(self, user: UserDict, data: EvalBody) -> JSONResponse:
        if not await Contract.exists(id=data.contract_id):
            raise HTTPException(
                status_code=404,
                detail=(
                    "you must provide a valid internal contract_id, "
                    "call /blockchain/scan first"
                ),
            )

        audit_type = data.audit_type
        # webhook_url = data.webhook_url

        audit = await Audit.create(
            contract_id=data.contract_id,
            app_id=user["app"].id,
            user_id=user["user"].id,
            audit_type=audit_type,
        )

        if (
            data.security_score is not None
            and data.project_type == AuditProjectTypeEnum.AGENT
        ):
            await self.add_agent_security_score(audit, data.security_score)

        redis_pool = await create_pool(redis_settings)

        # the job_id is guaranteed to be unique, make it align with the audit.id
        # for simplicitly.
        await redis_pool.enqueue_job(
            "process_eval",
            _job_id=str(audit.id),
        )

        return {"id": str(audit.id), "status": AuditStatusEnum.WAITING}

    async def get_eval(
        self, id: str, response_type: ResponseStructureEnum
    ) -> EvalResponse:
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
            "status": audit.status,
        }

        if audit.status == AuditStatusEnum.SUCCESS:
            if response_type == ResponseStructureEnum.RAW:
                data["result"] = audit.raw_output
            else:
                try:
                    data["result"] = self.sanitize_data(
                        audit=audit,
                        as_markdown=response_type == ResponseStructureEnum.MARKDOWN,
                    )
                except json.JSONDecodeError as err:
                    logging.error(
                        f"Unable to parse the output correctly for {str(audit.id)}: "
                        f"{err}"
                    )

        response.result = EvalResponseData(**data)

        return response
