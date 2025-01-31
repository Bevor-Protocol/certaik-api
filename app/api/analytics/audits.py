import base64
import math

import anyio
from fastapi import HTTPException
from tortoise.exceptions import DoesNotExist
from tortoise.timezone import now

from app.api.ai.eval import EvalService
from app.api.depends.auth import UserDict
from app.db.models import App, Audit, Contract, Finding, User
from app.pydantic.request import FeedbackBody
from app.pydantic.response import (
    AnalyticsAudit,
    AnalyticsContract,
    AnalyticsResponse,
    StatsResponse,
)
from app.utils.enums import AuditTypeEnum, FindingLevelEnum
from app.utils.typed import FilterParams


def encode_cursor(cursor: str) -> str:
    return base64.urlsafe_b64encode(cursor.encode()).decode()


def decode_cursor(cursor: str) -> str:
    return base64.urlsafe_b64decode(cursor.encode()).decode()


async def get_audits(user: UserDict, query: FilterParams) -> AnalyticsResponse:

    limit = query.page_size
    offset = query.page * limit

    filter = {}

    if query.search:
        filter["raw_output__icontains"] = query.search
    if query.audit_type:
        filter["audit_type__in"] = query.audit_type
    if query.network:
        filter["contract__network__in"] = query.network
    if query.contract_address:
        filter["contract__address__icontains"] = query.contract_address
    if query.user_id:
        filter["user__address__icontains"] = query.user_id

    if user["app"]:
        filter["app_id"] = user["app"].id
    else:
        filter["user_id"] = user["user"].id

    # TODO: remove this on launch.
    await anyio.sleep(2)

    audit_query = Audit.filter(**filter)

    total = await audit_query.count()

    total_pages = math.ceil(total / limit)

    if total <= (offset * limit):
        return AnalyticsResponse(results=[], more=False, total_pages=total_pages)

    results = (
        await audit_query.order_by("-created_at")
        .offset(offset)
        .limit(limit + 1)
        .values(
            "id",
            "created_at",
            "app_id",
            "user__address",
            "audit_type",
            "status",
            "contract__id",
            "contract__method",
            "contract__address",
            "contract__network",
        )
    )

    results_trimmed = results[:-1] if len(results) > limit else results

    data = []
    for i, result in enumerate(results_trimmed):
        contract = AnalyticsContract(
            id=result["contract__id"],
            method=result["contract__method"],
            address=result["contract__address"],
            network=result["contract__network"],
        )
        response = AnalyticsAudit(
            n=i + offset,
            id=result["id"],
            created_at=result["created_at"],
            app_id=str(result["app_id"]),
            user_id=result["user__address"],
            audit_type=result["audit_type"],
            status=result["status"],
            contract=contract,
        )
        data.append(response)

    return AnalyticsResponse(
        results=data, more=len(results) > query.page_size, total_pages=total_pages
    )


async def get_stats():
    await anyio.sleep(3)
    n_audits = 0
    n_contracts = await Contract.all().count()
    n_users = await User.all().count()
    n_apps = await App.all().count()

    n_audits = await Audit.all().count()
    findings = await Finding.all()

    gas_findings = {k.value: 0 for k in FindingLevelEnum}
    sec_findings = {k.value: 0 for k in FindingLevelEnum}

    for finding in findings:
        match finding.audit_type:
            case AuditTypeEnum.SECURITY:
                sec_findings[finding.level] += 1
            case AuditTypeEnum.GAS:
                gas_findings[finding.level] += 1

    response = StatsResponse(
        n_apps=n_apps,
        n_users=n_users,
        n_contracts=n_contracts,
        n_audits=n_audits,
        findings={
            AuditTypeEnum.GAS: gas_findings,
            AuditTypeEnum.SECURITY: sec_findings,
        },
    )

    return response


async def get_audit(id: str) -> str:
    audit = (
        await Audit.get(id=id)
        .select_related("contract", "user")
        .prefetch_related("findings")
    )

    result = None
    if audit.raw_output:
        eval_service = EvalService()
        result = eval_service.sanitize_data(audit=audit, as_markdown=True)

    findings = []
    finding: Finding
    for finding in audit.findings:
        findings.append(
            {
                "id": str(finding.id),
                "level": finding.level,
                "name": finding.name,
                "explanation": finding.explanation,
                "recommendation": finding.recommendation,
                "reference": finding.reference,
                "is_attested": finding.is_attested,
                "is_verified": finding.is_verified,
                "feedback": finding.feedback,
            }
        )

    return {
        "contract": {
            "address": audit.contract.address,
            "network": audit.contract.network,
            "code": audit.contract.raw_code,
        },
        "user": {
            "id": str(audit.user.id),
            "address": audit.user.address,
        },
        "audit": {
            "status": audit.status,
            "model": audit.model,
            "audit_type": audit.audit_type,
            "result": result,
        },
        "findings": findings,
    }


async def submit_feeback(data: FeedbackBody, user: UserDict) -> bool:

    try:
        finding = await Finding.get(id=data.id).select_related("audit__user")
    except DoesNotExist:
        raise HTTPException(status_code=401, detail="this finding does not exist")

    if finding.audit.user.address != user["user"].address:
        raise HTTPException(status_code=401, detail="user did not create this finding")

    finding.is_attested = True
    finding.is_verified = data.verified
    finding.feedback = data.feedback
    finding.attested_at = now()

    await finding.save()

    return True
