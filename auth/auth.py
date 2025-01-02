from typing import Any, Coroutine

from fastapi import Depends, HTTPException, Request, status
from config import SECRET_KEY

from fastapi_users.authentication import CookieTransport
from fastapi_users.authentication import JWTStrategy
from fastapi_users.authentication import AuthenticationBackend, JWTStrategy


from fastapi_users import FastAPIUsers
from auth.manager import get_user_manager
from auth.db import User

cookie_transport = CookieTransport(cookie_max_age=28800, cookie_httponly=True, cookie_secure=True, cookie_samesite='none')


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET_KEY, lifetime_seconds=28800)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)


fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

current_user = fastapi_users.current_user(active=True)

async def superuser_required(request: Request, user: str = Depends(current_user)):
    # Ваша логика проверки токена и получения пользователя
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You need to be a superuser to perform this action"
        )
    return user