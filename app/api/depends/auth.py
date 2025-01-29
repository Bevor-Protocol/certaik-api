import hashlib
from typing import Optional, TypedDict

from fastapi import HTTPException, Request
from tortoise.exceptions import DoesNotExist

from app.db.models import App, Auth, User
from app.utils.enums import AppTypeEnum, ClientTypeEnum


class UserDict(TypedDict):
    user: Optional[User]
    app: Optional[App]
    require_credit_and_limit: bool


async def require_auth(request: Request) -> UserDict:
    authorization = request.headers.get("authorization")
    address = request.headers.get("x-user-identifier")
    if not authorization:
        raise HTTPException(
            status_code=401, detail="proper authorization headers not provided"
        )
    api_key = authorization.split(" ")[1]
    try:
        auth = await Auth.get(
            hashed_key=hashlib.sha256(api_key.encode()).hexdigest()
        ).select_related("user", "app__owner")
        if auth.is_revoked:
            raise HTTPException(status_code=401, detail="This token was revoked")

        # request made on behalf of themselves
        if auth.client_type == ClientTypeEnum.USER:
            return UserDict(user=auth.user, require_credit_and_limit=True)
        else:
            response = UserDict(app=auth.app, require_credit_and_limit=True)
            if auth.app.type == AppTypeEnum.FIRST_PARTY:
                user = await User.get(address=address)
                response["user"] = user
                response["require_credit_and_limit"] = False
            else:
                if address:
                    user = await User.get(address=address)
                    response["user"] = user
                else:
                    response["user"] = auth.app.owner
        return response

    except DoesNotExist:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    except HTTPException as err:
        raise err


async def require_app(request: Request) -> str:
    authorization = request.headers.get("authorization")
    identifier = request.headers.get("x-user-identifier")

    if not authorization:
        raise HTTPException(
            status_code=401, detail="proper authorization headers not provided"
        )
    if not identifier:
        raise HTTPException(
            status_code=401,
            detail="to create a user, you must provide a x-user-identifier header",
        )
    api_key = authorization.split(" ")[1]

    try:
        auth = await Auth.get(
            hashed_key=hashlib.sha256(api_key.encode()).hexdigest()
        ).select_related("user", "app__owner")

        if auth.is_revoked:
            raise HTTPException(status_code=401, detail="This token was revoked")

        if auth.client_type == ClientTypeEnum.APP:
            if identifier:
                return identifier
        raise DoesNotExist()

    except DoesNotExist:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    except HTTPException as err:
        raise err


async def protected_first_party_app(request: Request) -> None:
    authorization = request.headers.get("authorization")
    if not authorization:
        raise HTTPException(
            status_code=401, detail="proper authorization headers not provided"
        )
    api_key = authorization.split(" ")[1]

    try:
        auth = await Auth.get(
            hashed_key=hashlib.sha256(api_key.encode()).hexdigest()
        ).select_related("user", "app__owner")

        if auth.is_revoked:
            raise HTTPException(status_code=401, detail="This token was revoked")

        if auth.client_type == ClientTypeEnum.APP:
            if auth.app.type == AppTypeEnum.FIRST_PARTY:
                return
        raise DoesNotExist()

    except DoesNotExist:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    except HTTPException as err:
        raise err
