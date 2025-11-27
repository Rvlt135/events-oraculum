from urllib.parse import urlencode

import httpx
import jwt

from app.config.settings import settings


class GoogleOAuthClient:
    AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v3/userinfo"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
    
    def get_authorization_url(self, oauth_params: dict) -> str:

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

    async def exchange_code(self, code: str, code_verifier: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_ENDPOINT,
                data={
                    "code": code,
                    "code_verifier": code_verifier,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            return response.json()

    def verify_id_token(self, id_token: str, cached_nonce: str) -> dict:
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
            if payload.get("nonce") != cached_nonce:
                raise ValueError("Invalid nonce")
            return payload
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid ID token: {e!s}")

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
