from fastapi import APIRouter

from .admin.router import AdminRouter
from .app.router import AppRouter
from .audit.router import AuditRouter
from .auth.router import AuthRouter
from .base.router import BaseRouter
from .blockchain.router import BlockchainRouter
from .contract.router import ContractRouter
from .platform.router import PlatformRouter
from .user.router import UserRouter


def construct_router():
    router = APIRouter()

    router.include_router(AdminRouter())
    router.include_router(AppRouter())
    router.include_router(AuditRouter())
    router.include_router(AuthRouter())
    router.include_router(BaseRouter())
    router.include_router(BlockchainRouter())
    router.include_router(ContractRouter())
    router.include_router(PlatformRouter())
    router.include_router(UserRouter())

    return router


router = construct_router()
