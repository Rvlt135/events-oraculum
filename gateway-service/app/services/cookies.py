from fastapi import Response

from app.config.settings import settings


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.access_token_cookie_name,
        value=access_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="Lax",
        path="/",
        max_age=settings.auth_access_ttl_sec,
    )

    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="Strict",
        path="/",
        max_age=settings.auth_refresh_ttl_sec,
    )