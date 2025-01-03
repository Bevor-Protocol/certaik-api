from enum import Enum


class PlatformEnum(Enum):
    ETH = "ETH"
    BSC = "BSC"
    POLYGON = "POLYGON"
    BASE = "BASE"
    ETH_SEPOLIA = "ETH_SEPOLIA"
    BSC_TEST = "BSC_TEST"
    POLYGON_AMOY = "POLYGON_AMOY"
    BASE_SEPOLIA = "BASE_SEPOLIA"


class NetworkTypeEnum(Enum):
    TESTNET = "TESTNET"
    MAINNET = "MAINNET"


class AuditTypeEnum(Enum):
    SECURITY = "security"
    GAS = "gas"


class AuditStatusEnum(Enum):
    WAITING = "waiting"
    SUCCESS = "success"
    FAILED = "failed"


class ResponseStructureEnum(Enum):
    RAW = "raw"
    JSON = "json"
    MARKDOWN = "markdown"
