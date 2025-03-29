from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.api.auth.service import AuthService
from app.api.blockchain.service import BlockchainService
from app.api.dependencies import Authentication
from app.db.models import Transaction, User
from app.utils.logger import get_logger
from app.utils.schema.dependencies import AuthState
from app.utils.types.enums import ClientTypeEnum, RoleEnum, TransactionTypeEnum

logger = get_logger("api")


class AuthRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/auth", include_in_schema=False)

        self.add_api_route(
            "/{client_type}",
            self.generate_api_key,
            methods=["POST"],
            dependencies=[
                Depends(Authentication(required_role=RoleEnum.APP_FIRST_PARTY))
            ],
            include_in_schema=False,
        )
        self.add_api_route(
            "/sync/credits",
            self.sync_credits,
            methods=["POST"],
            dependencies=[Depends(Authentication(required_role=RoleEnum.USER))],
            include_in_schema=False,
        )

    async def generate_api_key(self, request: Request, client_type: ClientTypeEnum):
        auth_service = AuthService()

        api_key = await auth_service.generate(
            auth_obj=request.state.auth, client_type=client_type
        )

        return JSONResponse({"api_key": api_key}, status_code=status.HTTP_202_ACCEPTED)

    async def sync_credits(self, request: Request):
        blockchain_service = BlockchainService()

        auth: AuthState = request.state.auth
        try:
            user = await User.get(id=auth.user_id)
            credits = await blockchain_service.get_credits(user.address)
        except Exception as err:
            logger.exception(err)
            return JSONResponse(
                {"success": False, "error": "could not connect to network"},
                status_code=status.HTTP_200_OK,
            )

        prev_credits = user.total_credits
        diff = credits - prev_credits
        user.total_credits = credits
        await user.save()
        if abs(diff) > 0:
            transaction = Transaction(
                app_id=auth.app_id, user_id=auth.user_id, amount=abs(diff)
            )
            if diff > 0:
                transaction.type = TransactionTypeEnum.PURCHASE
            else:
                transaction.type = TransactionTypeEnum.REFUND
            await transaction.save()

        return JSONResponse(
            {
                "total_credits": credits,
                "credits_added": max(0, diff),
                "credits_removed": abs(min(0, diff)),  # only applicable during refund.
            },
            status_code=status.HTTP_200_OK,
        )
