from tortoise import fields

from app.db.models.abstract import AbstractModel
from app.utils.enums import AuditTypeEnum, PlatformEnum


class Contract(AbstractModel):
    contract_platform = fields.CharEnumField(PlatformEnum)
    contract_address = fields.TextField()
    audit_type = fields.CharEnumField(AuditTypeEnum)
    audit_results = fields.TextField()

    def __str__(self):
        return f"{self.id} | {self.address}"
