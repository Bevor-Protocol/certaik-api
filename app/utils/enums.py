from enum import Enum

# Inheriting (str, Enum) makes it serializable in the response


class ContractMethodEnum(str, Enum):
    UPLOAD = "upload"
    SCAN = "scan"
    CRON = "cron"


class NetworkEnum(str, Enum):
    ETH = "eth"
    BSC = "bsc"
    POLYGON = "polygon"
    BASE = "base"
    ETH_SEPOLIA = "eth_sepolia"
    BSC_TEST = "bsc_test"
    POLYGON_AMOY = "polygon_amoy"
    BASE_SEPOLIA = "base_sepolia"


class NetworkTypeEnum(str, Enum):
    TESTNET = "testnet"
    MAINNET = "mainnet"


class AuditTypeEnum(str, Enum):
    SECURITY = "security"
    GAS = "gas"


class AuditStatusEnum(str, Enum):
    WAITING = "waiting"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class ResponseStructureEnum(str, Enum):
    RAW = "raw"
    JSON = "json"
    MARKDOWN = "markdown"


class ModelTypeEnum(str, Enum):
    LLAMA3 = "llama3"
    OPENAI = "openai"


class CreditTierEnum(str, Enum):
    FREE = "free"
    BASIC = "basic"


class TransactionTypeEnum(str, Enum):
    PURCHASE = "purchase"
    USE = "spend"
    REFUND = "refund"


class ClientTypeEnum(str, Enum):
    USER = "user"
    APP = "app"


class AppTypeEnum(str, Enum):
    FIRST_PARTY = "first_party"
    THIRD_PARTY = "third_party"


class WebhookEventEnum(str, Enum):
    EVAL_UPDATED = "eval.updated"
