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
    AVAX = "avax"
    MODE = "mode"
    ARB = "arb"
    ETH_SEPOLIA = "eth_sepolia"
    BSC_TEST = "bsc_test"
    POLYGON_AMOY = "polygon_amoy"
    BASE_SEPOLIA = "base_sepolia"
    AVAX_FUJI = "avax_fuji"
    MODE_TESTNET = "mode_testnet"
    ARB_SEPOLIA = "arb_sepolia"


class NetworkTypeEnum(str, Enum):
    TESTNET = "testnet"
    MAINNET = "mainnet"


class AuditTypeEnum(str, Enum):
    SECURITY = "security"
    GAS = "gas"


class AuditProjectTypeEnum(str, Enum):
    AGENT = "agent"
    PROTOCOL = "protocol"
    TOKEN = "token"
    NFT = "nft"


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


class IntermediateResponseEnum(str, Enum):
    CANDIDATE = "candidate"
    REVIEWER = "reviewer"
    REPORTER = "reporter"


class FindingLevelEnum(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
