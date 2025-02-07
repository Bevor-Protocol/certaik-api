from typing import Optional
from xmlrpc.client import boolean

from pydantic import BaseModel, Field

from app.utils.enums import (
    AuditProjectTypeEnum,
    AuditTypeEnum,
    ModelTypeEnum,
    NetworkEnum,
)


class EvalBody(BaseModel):
    contract_id: str
    audit_type: AuditTypeEnum = Field(default=AuditTypeEnum.GAS)
    model_type: Optional[ModelTypeEnum] = Field(default=ModelTypeEnum.LLAMA3)
    security_score: Optional[float] = Field(default=None)
    project_type: Optional[AuditProjectTypeEnum] = Field(default=None)
    webhook_url: Optional[str] = Field(default=None)


class ContractUploadBody(BaseModel):
    code: str
    network: Optional[NetworkEnum] = Field(default=None)


class FeedbackBody(BaseModel):
    id: str
    feedback: Optional[str] = Field(default=None)
    verified: boolean
