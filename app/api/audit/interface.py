from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.utils.types.models import (
    AuditSchema,
    BaseSchema,
    ContractSchema,
    FindingSchema,
    IntermediateResponseSchema,
    UserSchema,
)
from app.utils.types.shared import IdResponse
from app.utils.types.enums import AuditStatusEnum, AuditTypeEnum, NetworkEnum
from app.utils.types.mixins import FkMixin

"""
Used for HTTP request validation, response Serialization, and arbitrary typing.
"""


class EvalBody(BaseModel):
    contract_id: str = Field(description="contract to evaluate")
    audit_type: AuditTypeEnum = Field(default=AuditTypeEnum.GAS)


class CreateEvalResponse(IdResponse):
    status: AuditStatusEnum = Field(description="initial status of created audit")


class FeedbackBody(BaseModel):
    feedback: Optional[str] = Field(default=None)
    verified: bool


class FilterParams(BaseModel, FkMixin):
    user_id: Optional[str | UUID] = None
    user_address: Optional[str] = None
    page: int = 0
    page_size: int = 20
    search: Optional[str] = Field(default=None, description="search the audit result")
    audit_type: list[AuditTypeEnum] = Field(default_factory=list)
    status: Optional[AuditStatusEnum] = None
    network: list[NetworkEnum] = Field(default_factory=list)
    contract_address: Optional[str] = None

    @field_validator("audit_type", mode="before")
    @classmethod
    def parse_audit_to_list(cls, value: list[str] | str):
        if not value:
            return []
        if (
            isinstance(value, list)
            and len(value) == 1
            and isinstance(value[0], str)
            and "," in value[0]
        ):
            return value[0].replace("%2C", ",").split(",")
        if isinstance(value, str):
            value = value.replace("%2C", ",")
            return value.split(",")
        return value

    @field_validator("network", mode="before")
    @classmethod
    def parse_network_to_list(cls, value: list[str] | str):
        if not value:
            return []
        if (
            isinstance(value, list)
            and len(value) == 1
            and isinstance(value[0], str)
            and "," in value[0]
        ):
            return value[0].replace("%2C", ",").split(",")
        if isinstance(value, str):
            value = value.replace("%2C", ",")
            return value.split(",")
        return value


class AuditMetadata(BaseSchema):
    n: int
    audit_type: AuditTypeEnum
    status: AuditStatusEnum
    contract: ContractSchema
    user: UserSchema


class AuditsResponse(BaseModel):
    results: list[AuditMetadata] = Field(
        default_factory=lambda: [], description="array of audits"
    )
    more: bool = Field(
        description="whether more audits exist, given page and page_size"
    )
    total_pages: int = Field(description="total pages, given page_size")


class AuditResponse(AuditSchema):
    findings: list[FindingSchema] = Field(default_factory=lambda: [])
    contract: ContractSchema
    user: UserSchema


class GetAuditStatusResponse(BaseModel):
    status: AuditStatusEnum = Field(
        description="status of entire audit, depends on steps"
    )
    steps: list[IntermediateResponseSchema] = Field(default_factory=lambda: [])
