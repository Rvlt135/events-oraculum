from datetime import datetime, timedelta, UTC
from uuid import UUID, uuid4
import jwt
from pydantic import BaseModel

class TokenPayload(BaseModel):
    sub: str
    jti: str
    exp: int
    iat: int
    type: str
    plan: str | None = None
    aid: int | None = None


class JWTService:
    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        access_ttl: int = 900,
        refresh_ttl: int = 1209600,
    ):
        # Ensure secret is a string
        self.secret = str(secret)
        self.algorithm = algorithm
        self.access_ttl = access_ttl
        self.refresh_ttl = refresh_ttl

    def create_access_token(
        self, user_id: UUID, plan_type: str, account_id: int | None = None
    ) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "jti": str(uuid4()),
            "exp": int((now + timedelta(seconds=self.access_ttl)).timestamp()),
            "iat": int(now.timestamp()),
            "type": "access",
            "plan": plan_type,
        }
        if account_id is not None:
            payload["aid"] = account_id
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        # Ensure token is a string (PyJWT 2.x returns str, but 1.x returns bytes)
        if isinstance(token, bytes):
            return token.decode("utf-8")
        return token

    def create_refresh_token(self, user_id: UUID, jti: UUID | None = None) -> tuple[str, UUID]:
        if jti is None:
            jti = uuid4()
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "jti": str(jti),
            "exp": int((now + timedelta(seconds=self.refresh_ttl)).timestamp()),
            "iat": int(now.timestamp()),
            "type": "refresh",
        }
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        # Ensure token is a string (PyJWT 2.x returns str, but 1.x returns bytes)
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        return token, jti

    def verify_token(self, token: str, expected_type: str = "access") -> TokenPayload:
        try:
            # Ensure token is a string
            token_str = str(token) if token else ""
            if not token_str:
                raise ValueError("Token is required")
            
            # Use the stored secret (already ensured to be string in __init__)
            payload = jwt.decode(token_str, self.secret, algorithms=[self.algorithm])
            token_data = TokenPayload(**payload)
            if token_data.type != expected_type:
                raise ValueError(f"Invalid token type: expected {expected_type}, got {token_data.type}")
            return token_data
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")

