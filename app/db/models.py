import hashlib
import secrets

from tortoise import fields
from tortoise.models import Model

from app.utils.enums import (
    AppTypeEnum,
    AuditProjectTypeEnum,
    AuditStatusEnum,
    AuditTypeEnum,
    ClientTypeEnum,
    ContractMethodEnum,
    CreditTierEnum,
    FindingLevelEnum,
    IntermediateResponseEnum,
    NetworkEnum,
    TransactionTypeEnum,
    WebhookEventEnum,
)


class AbstractModel(Model):
    id = fields.UUIDField(primary_key=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.id)


class User(AbstractModel):
    address = fields.CharField(max_length=255, unique=True)
    total_credits = fields.IntField(default=0)
    remaining_credits = fields.IntField(default=0)

    class Meta:
        table = "user"
        indexes = ("address",)

    def __str__(self):
        return f"{str(self.id)} | {self.address}"


class App(AbstractModel):
    # Every app will have an owner, unless it's a first party app.
    owner: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", on_delete=fields.SET_NULL, null=True, related_name="app"
    )
    name = fields.CharField(max_length=255)
    type = fields.CharEnumField(enum_type=AppTypeEnum, default=AppTypeEnum.THIRD_PARTY)

    class Meta:
        table = "app"
        indexes = ("type",)

    def __str__(self):
        return f"{str(self.id)} | {self.name} | {self.type}"


class Auth(AbstractModel):
    app: fields.ForeignKeyRelation[App] = fields.ForeignKeyField(
        "models.App", on_delete=fields.SET_NULL, null=True
    )
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", on_delete=fields.SET_NULL, null=True
    )
    client_type = fields.CharEnumField(
        enum_type=ClientTypeEnum, default=ClientTypeEnum.USER
    )
    hashed_key = fields.CharField(max_length=255)
    is_revoked = fields.BooleanField(default=False)

    class Meta:
        table = "auth"
        indexes = ("hashed_key",)

    def __str__(self):
        return str(self.id)

    @staticmethod
    def create_credentials():
        api_key = secrets.token_urlsafe(32)
        hashed_key = hashlib.sha256(api_key.encode()).hexdigest()
        return api_key, hashed_key

    @staticmethod
    def hash_key(api_key: str):
        return hashlib.sha256(api_key.encode()).hexdigest()


class Credit(AbstractModel):
    tier = fields.CharEnumField(enum_type=CreditTierEnum)
    value = fields.FloatField(default=1.0)

    class Meta:
        table = "credit"

    def __str__(self):
        return f"{self.tier} | {self.value} credits per request"


class Transaction(AbstractModel):
    app: fields.ForeignKeyRelation[App] = fields.ForeignKeyField(
        "models.App", on_delete=fields.SET_NULL, null=True, related_name="transactions"
    )
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", on_delete=fields.SET_NULL, null=True, related_name="transactions"
    )
    type = fields.CharEnumField(enum_type=TransactionTypeEnum)
    amount = fields.FloatField()

    class Meta:
        table = "transaction"

    def __str__(self):
        return f"{str(self.id)} | {self.type} | {self.amount}"


class Contract(AbstractModel):
    method = fields.CharEnumField(enum_type=ContractMethodEnum)
    is_available = fields.BooleanField(
        default=True, description="if via cron, whether source code is available"
    )
    n_retries = fields.IntField(
        default=0, description="current # of retries to get source code"
    )
    next_attempt_at = fields.DatetimeField(
        auto_now=True,
        description="if source code unavailable, next timestamp to allow scan",
    )
    address = fields.CharField(max_length=255, null=True, default=None)
    network = fields.CharEnumField(enum_type=NetworkEnum, null=True, default=None)
    raw_code = fields.TextField(null=True, default=None)
    hash_code = fields.CharField(max_length=255, null=True, default=None)

    class Meta:
        table = "contract"

    def __str__(self):
        return f"{str(self.id)} | {self.job_id}"

    @classmethod
    async def create(self, *args, **kwargs):
        raw_code = kwargs.get("raw_code")
        if raw_code:
            kwargs["hash_code"] = hashlib.sha256(raw_code.encode()).hexdigest()
        return await super().create(*args, **kwargs)

    async def save(self, *args, **kwargs):
        raw_code = kwargs.get("raw_code")
        if raw_code:
            kwargs["hash_code"] = hashlib.sha256(raw_code.encode()).hexdigest()
        await super().save(*args, **kwargs)


class Audit(AbstractModel):
    app: fields.ForeignKeyRelation[App] = fields.ForeignKeyField(
        "models.App", on_delete=fields.SET_NULL, null=True, related_name="audits"
    )
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", on_delete=fields.SET_NULL, null=True, related_name="audits"
    )
    contract: fields.ForeignKeyRelation[Contract] = fields.ForeignKeyField(
        "models.Contract", on_delete=fields.CASCADE, related_name="audits"
    )
    model = fields.CharField(max_length=255, null=True, default=None)
    audit_type = fields.CharEnumField(enum_type=AuditTypeEnum)
    project_type = fields.CharEnumField(
        enum_type=AuditProjectTypeEnum, null=True, default=AuditProjectTypeEnum.PROTOCOL
    )
    security_score = fields.FloatField(null=True, default=None)
    processing_time_seconds = fields.IntField(null=True, default=None)
    status = fields.CharEnumField(
        enum_type=AuditStatusEnum, null=True, default=AuditStatusEnum.WAITING
    )
    raw_output = fields.TextField(null=True, default=None)

    class Meta:
        table = "audit"
        indexes = (
            ("user_id",),
            ("user_id", "audit_type", "contract_id"),
            ("user_id", "audit_type"),
            ("audit_type", "contract_id"),
        )

    def __str__(self):
        return f"{str(self.id)} | {self.job_id}"


class IntermediateResponse(AbstractModel):
    audit: fields.ForeignKeyRelation[Audit] = fields.ForeignKeyField(
        "models.Audit", on_delete=fields.CASCADE, related_name="intermediate_responses"
    )
    step = fields.CharEnumField(enum_type=IntermediateResponseEnum)
    result = fields.TextField()

    class Meta:
        table = "intermediate_response"

    def __str__(self):
        return f"{str(self.id)} | {self.audit_id}"


class Finding(AbstractModel):
    audit: fields.ForeignKeyRelation[Audit] = fields.ForeignKeyField(
        "models.Audit", on_delete=fields.CASCADE, related_name="findings"
    )
    audit_type = fields.CharEnumField(enum_type=AuditTypeEnum)
    level = fields.CharEnumField(enum_type=FindingLevelEnum)
    name = fields.TextField(null=True, default=None)
    explanation = fields.TextField(null=True, default=None)
    recommendation = fields.TextField(null=True, default=None)
    reference = fields.TextField(null=True, default=None)
    is_attested = fields.BooleanField(default=False)
    is_verified = fields.BooleanField(default=False)
    feedback = fields.TextField(null=True, default=None)
    attested_at = fields.DatetimeField(null=True, default=None)

    class Meta:
        table = "finding"

    def __str__(self):
        return f"{str(self.id)} | {self.audit_id}"


class Webhook(AbstractModel):
    app: fields.ForeignKeyRelation[App] = fields.ForeignKeyField(
        "models.App", on_delete=fields.SET_NULL, null=True, related_name="webhooks"
    )
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", on_delete=fields.SET_NULL, null=True, related_name="webhooks"
    )
    url = fields.CharField(max_length=255)
    event = fields.CharEnumField(enum_type=WebhookEventEnum)
    is_enabled = fields.BooleanField(default=True)
    failure_count = fields.IntField(default=0)
    last_failure = fields.DatetimeField(null=True)
    last_success = fields.DatetimeField(null=True)
    next_retry = fields.DatetimeField(null=True)

    class Meta:
        table = "webhook"

    def __str__(self):
        return f"{str(self.id)} | {self.url}"
