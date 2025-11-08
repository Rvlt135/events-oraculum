from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
import jwt

from app.config.settings import settings
from app.infrastructure.cache.redis import redis_cache_manager
from app.infrastructure.security.utils import generate_oauth_params
from app.services.google_oauth_validator import google_oauth_validator


class GoogleOAuthClient:
    AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v3/userinfo"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
    
    async def save_to_redis(self, params: dict, ttl: int = 600) -> None:
        """
        Сохранение OAuth параметров в Redis
        
        Args:
            params: словарь с OAuth параметрами
            ttl: время жизни в секундах (по умолчанию 600 = 10 минут)
        """
        state = params.pop("state")
        state_key = f"oauth:state:{state}"
        await redis_cache_manager.set(state_key, params, ttl)

    async def get_authorization_url(self, header: dict, return_to: str | None = None) -> str:

        return_to = google_oauth_validator.validate_and_parse_return_path(return_to)

        oauth_params = generate_oauth_params()

        cached_params = {
            "provider": "GOOGLE",
            "nonce": oauth_params.get("nonce"),
            "code_verifier": oauth_params.get("code_verifier"),
            "state": oauth_params.get("state"),
            "return_to": return_to,
            "redirect_uri": self.redirect_uri,
            "ip": "<client_ip>",
            "ua": header.get("user-agent"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "PENDING",
        }

        await self.save_to_redis(cached_params)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": oauth_params.get("state"),
            "nonce": oauth_params.get("nonce"),
            "code_challenge": oauth_params.get("code_challenge"),
            "code_challenge_method": oauth_params.get("code_challenge_method"),
            "access_type": "offline",
        }

        return f"{self.AUTHORIZATION_ENDPOINT}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_ENDPOINT,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            return response.json()

    def verify_id_token(self, id_token: str) -> dict:
        try:
            payload = jwt.decode(
                id_token,
                options={"verify_signature": False},
            )
            if payload.get("aud") != self.client_id:
                raise ValueError("Invalid audience")
            if payload.get("iss") not in [
                "https://accounts.google.com",
                "accounts.google.com",
            ]:
                raise ValueError("Invalid issuer")
            return payload
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid ID token: {str(e)}")

    async def get_user_info(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USERINFO_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()


google_oauth_client = GoogleOAuthClient(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
    )
