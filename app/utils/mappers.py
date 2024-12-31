import os

from .enums import NetworkTypeEnum, PlatformEnum

platform_explorer_mapper = {
    PlatformEnum.BASE: "api.basescan.org",
    PlatformEnum.BASE_SEPOLIA: "api.api-sepolia.basescan.org",
    PlatformEnum.BSC: "api.bscscan.com",
    PlatformEnum.BSC_TEST: "api.api-testnet.bscscan.com",
    PlatformEnum.ETH: "api.etherscan.io",
    PlatformEnum.ETH_SEPOLIA: "api.api-sepolia.etherscan.io",
    PlatformEnum.POLYGON: "api.polygonscan.com",
    PlatformEnum.POLYGON_AMOY: "api.api-amoy.polygonscan.com",
}

platform_explorer_apikey_mapper = {
    PlatformEnum.BASE: os.getenv("BASESCAN_API_KEY"),
    PlatformEnum.BASE_SEPOLIA: os.getenv("BASESCAN_API_KEY"),
    PlatformEnum.BSC: os.getenv("BSCSCAN_API_KEY"),
    PlatformEnum.BSC_TEST: os.getenv("BSCSCAN_API_KEY"),
    PlatformEnum.ETH: os.getenv("ETHERSCAN_API_KEY"),
    PlatformEnum.ETH_SEPOLIA: os.getenv("ETHERSCAN_API_KEY"),
    PlatformEnum.POLYGON: os.getenv("POLYGONSCAN_API_KEY"),
    PlatformEnum.POLYGON_AMOY: os.getenv("POLYGONSCAN_API_KEY"),
}

platform_rpc_mapper = {
    PlatformEnum.BASE: "base-mainnet.g.alchemy.com",
    PlatformEnum.BASE_SEPOLIA: "base-sepolia.g.alchemy.com",
    PlatformEnum.BSC: "bnb-mainnet.g.alchemy.com",
    PlatformEnum.BSC_TEST: "bnb-testnet.g.alchemy.com",
    PlatformEnum.ETH: "eth-mainnet.g.alchemy.com",
    PlatformEnum.ETH_SEPOLIA: "eth-sepolia.g.alchemy.com",
    PlatformEnum.POLYGON: "polygon-mainnet.g.alchemy.com",
    PlatformEnum.POLYGON_AMOY: "polygon-amoy.g.alchemy.com",
}

platform_types = {
    NetworkTypeEnum.MAINNET: [
        PlatformEnum.BASE,
        PlatformEnum.BSC,
        PlatformEnum.ETH,
        PlatformEnum.POLYGON,
    ],
    NetworkTypeEnum.TESTNET: [
        PlatformEnum.BASE_SEPOLIA,
        PlatformEnum.BSC_TEST,
        PlatformEnum.ETH_SEPOLIA,
        PlatformEnum.POLYGON_AMOY,
    ],
}
