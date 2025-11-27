from fastapi import Response, Request

from app.config.settings import settings


def get_auth_cookies(response: Request) -> dict:
    return {
        "access_token": response.cookies.get(settings.access_token_cookie_name),
        "refresh_token": response.cookies.get(settings.refresh_token_cookie_name),
    }


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:

    response.set_cookie(
        key=settings.access_token_cookie_name,
        value=access_token,
        httponly=True,
        domain=settings.auth_cookie_domain,
        secure=settings.auth_cookie_secure,
        samesite="Lax",
        path="/",
        max_age=settings.auth_access_ttl_sec,
    )
    
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=refresh_token,
        httponly=True,
        domain=settings.auth_cookie_domain,
        secure=settings.auth_cookie_secure,
        samesite="Strict",
        path="/",
        max_age=settings.auth_refresh_ttl_sec,
    )

def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=settings.access_token_cookie_name,
        domain=settings.auth_cookie_domain,
        path="/",
    )
    response.delete_cookie(
        key=settings.refresh_token_cookie_name,
        domain=settings.auth_cookie_domain,
        path="/",
    )
