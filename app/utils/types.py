from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.utils.enums import AuditTypeEnum, PlatformEnum, ModelTypeEnum


class EvalBody(BaseModel):
    contract_code: Optional[str] = Field(default=None)
    contract_address: Optional[str] = Field(default=None)
    network: Optional[PlatformEnum] = Field(default=None)
    audit_type: AuditTypeEnum = Field(default=AuditTypeEnum.GAS)
    encode_code: bool = Field(default=False)
    model_type: ModelTypeEnum = Field(default=ModelTypeEnum.LLAMA3)
    as_markdown: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_contract_inputs(self) -> "EvalBody":
        if not self.contract_code and not self.contract_address:
            raise ValueError(
                "Either contract_code or contract_address must be provided"
            )

        if self.contract_address and not self.network:
            raise ValueError("network is required when contract_address is provided")

        return self
