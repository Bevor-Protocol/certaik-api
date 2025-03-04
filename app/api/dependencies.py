"""
Acts a bit differently from middleware, as we inject these on a per-request
basis. Fundamentally acts as a middleware, but we have more control over when its
used without explicitly needing to whitelist / blacklist routes.
"""

import logging
from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import redis_client
from app.db.models import Auth, User
from app.utils.schema.dependencies import AuthState
from app.utils.types.enums import AppTypeEnum, AuthScopeEnum, ClientTypeEnum, RoleEnum

security = HTTPBearer(description="API key authorization")


class Authentication:
    def __init__(
        self,
        required_role: RoleEnum,
        scope_override: Optional[AuthScopeEnum] = None,
    ):
        self.required_role = required_role
        self.scope_override = scope_override

    async def check_authentication(
        self, request: Request, credentials: str, user_identifier: Optional[str] = None
    ) -> Auth:
        hashed_key = Auth.hash_key(credentials)
        auth = await Auth.get(hashed_key=hashed_key).select_related(
            "user", "app__owner"
        )

        if auth.revoked_at:
            raise Exception("api key revoked")

        app = auth.app
        user = auth.user

        if self.required_role == RoleEnum.APP_FIRST_PARTY:
            if not app:
                raise Exception("invalid api permissions")
            if auth.client_type != ClientTypeEnum.APP:
                raise Exception("invalid api permissions")
            if app.type != AppTypeEnum.FIRST_PARTY:
                raise Exception("invalid api permissions")

        if self.required_role == RoleEnum.APP:
            if not app:
                raise Exception("invalid api permissions")
            if auth.client_type != ClientTypeEnum.APP:
                raise Exception("invalid api permissions")

        is_delegated = user_identifier is not None
        credit_consumer_user_id = None
        consumes_credits = auth.consumes_credits
        app_id = None
        user_id = None

        if auth.client_type == ClientTypeEnum.APP:
            app_id = app.id
            if app.type == AppTypeEnum.FIRST_PARTY:
                consumes_credits = False
                role = RoleEnum.APP_FIRST_PARTY
                user_id = user_identifier
            else:
                role = RoleEnum.APP
                credit_consumer_user_id = app.owner.id
                user_id = app.owner.id if not is_delegated else user_identifier
        else:
            credit_consumer_user_id = user.id
            role = RoleEnum.USER
            user_id = user.id

        auth_state = AuthState(
            role=role,
            consumes_credits=consumes_credits,
            credit_consumer_user_id=credit_consumer_user_id,
            is_delegated=is_delegated,
            user_id=user_id,
            app_id=app_id,
        )

        request.state.auth = auth_state

        return auth

    async def check_authorization(self, request: Request, auth: Auth) -> None:
        method = request.method
        cur_scope = auth.scope
        required_scope = self.scope_override
        if not required_scope:
            if method == "GET":
                required_scope = AuthScopeEnum.READ
            else:
                required_scope = AuthScopeEnum.WRITE

        if required_scope == AuthScopeEnum.ADMIN:
            if cur_scope != AuthScopeEnum.ADMIN:
                raise Exception("invalid scope for this request")
        if required_scope == AuthScopeEnum.WRITE:
            if cur_scope not in [AuthScopeEnum.ADMIN, AuthScopeEnum.WRITE]:
                raise Exception("invalid scope for this request")

    async def __call__(
        self,
        request: Request,
        authorization: Annotated[HTTPAuthorizationCredentials, Depends(security)],
        x_user_identifier: Optional[str] = Header(
            None,
            description="Unique user identifier (optional). Only relevant for `App` role",  # noqa
        ),
    ) -> None:
        try:
            auth = await self.check_authentication(
                request=request,
                credentials=authorization.credentials,
                user_identifier=x_user_identifier,
            )
            await self.check_authorization(request=request, auth=auth)
        except Exception as err:
            logging.exception(err)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err)
            )


class AuthenticationWithoutDelegation:
    def __init__(
        self,
        required_role: RoleEnum,
        scope_override: Optional[AuthScopeEnum] = None,
    ):
        self.required_role = required_role
        self.scope_override = scope_override

    async def check_authentication(self, request: Request, credentials: str) -> Auth:
        hashed_key = Auth.hash_key(credentials)
        auth = await Auth.get(hashed_key=hashed_key).select_related(
            "user", "app__owner"
        )

        if auth.revoked_at:
            raise Exception("api key revoked")

        app = auth.app
        user = auth.user

        if self.required_role == RoleEnum.APP_FIRST_PARTY:
            if not app:
                raise Exception("invalid api permissions")
            if auth.client_type != ClientTypeEnum.APP:
                raise Exception("invalid api permissions")
            if app.type != AppTypeEnum.FIRST_PARTY:
                raise Exception("invalid api permissions")

        if self.required_role == RoleEnum.APP:
            if not app:
                raise Exception("invalid api permissions")
            if auth.client_type != ClientTypeEnum.APP:
                raise Exception("invalid api permissions")

        credit_consumer_user_id = None
        consumes_credits = auth.consumes_credits
        app_id = None
        user_id = None

        if auth.client_type == ClientTypeEnum.APP:
            app_id = app.id
            if app.type == AppTypeEnum.FIRST_PARTY:
                consumes_credits = False
                role = RoleEnum.APP_FIRST_PARTY

            else:
                role = RoleEnum.APP
                credit_consumer_user_id = app.owner.id
                user_id = app.owner.id
        else:
            credit_consumer_user_id = user.id
            role = RoleEnum.USER
            user_id = user.id

        auth_state = AuthState(
            role=role,
            consumes_credits=consumes_credits,
            credit_consumer_user_id=credit_consumer_user_id,
            is_delegated=False,
            user_id=user_id,
            app_id=app_id,
        )

        request.state.auth = auth_state

        return auth

    async def check_authorization(self, request: Request, auth: Auth) -> None:
        method = request.method
        cur_scope = auth.scope
        required_scope = self.scope_override
        if not required_scope:
            if method == "GET":
                required_scope = AuthScopeEnum.READ
            else:
                required_scope = AuthScopeEnum.WRITE

        if required_scope == AuthScopeEnum.ADMIN:
            if cur_scope != AuthScopeEnum.ADMIN:
                raise Exception("invalid scope for this request")
        if required_scope == AuthScopeEnum.WRITE:
            if cur_scope not in [AuthScopeEnum.ADMIN, AuthScopeEnum.WRITE]:
                raise Exception("invalid scope for this request")

    async def __call__(
        self,
        request: Request,
        authorization: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    ) -> None:
        try:
            auth = await self.check_authentication(
                request=request,
                credentials=authorization.credentials,
            )
            await self.check_authorization(request=request, auth=auth)
        except Exception as err:
            logging.exception(err)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err)
            )


class RequireCredits:
    """
    Dependency that dictates whether credits are required to take an action.
    Requires authentication, as we rely on the request.state.auth object to
    be injected into the request.
    """

    def __init__(self):
        pass

    async def __call__(self, request: Request) -> None:
        if not request.state.auth:
            raise NotImplementedError("Authentication must be called")

        auth: AuthState = request.state.auth

        if not auth.consumes_credits:
            return

        if auth.credit_consumer_user_id:
            user = await User.get(id=auth.credit_consumer_user_id)
            if user.total_credits > 0:
                if user.used_credits < user.total_credits:
                    return

        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="insufficient credits to make request",
        )


class RateLimit:
    MAX_LIMIT_PER_MINUTE = 30
    WINDOW_SECONDS = 60

    def __init__(self):
        pass

    async def __call__(self, request: Request) -> None:
        auth: AuthState = request.state
        if auth["app"]:
            if auth["app"].type == AppTypeEnum.FIRST_PARTY:
                return

        authorization = request.headers.get("authorization")
        api_key = authorization.split(" ")[1]
        redis_key = f"rate_limit|{api_key}"

        current_time = int(datetime.now().timestamp())
        await redis_client.ltrim(redis_key, 0, self.MAX_LIMIT_PER_MINUTE)
        await redis_client.lrem(redis_key, 0, current_time - self.WINDOW_SECONDS)

        request_count = await redis_client.llen(redis_key)

        if request_count >= self.MAX_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests in a minute",
            )

        await redis_client.rpush(redis_key, current_time)
        await redis_client.expire(redis_client, self.WINDOW_SECONDS)
