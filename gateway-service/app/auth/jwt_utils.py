from datetime import datetime, timedelta
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
        self.secret = secret
        self.algorithm = algorithm
        self.access_ttl = access_ttl
        self.refresh_ttl = refresh_ttl

    def create_access_token(
        self, user_id: UUID, plan_type: str, account_id: int | None = None
    ) -> str:
        now = datetime.utcnow()
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
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: UUID, jti: UUID | None = None) -> tuple[str, UUID]:
        if jti is None:
            jti = uuid4()
        now = datetime.utcnow()
        payload = {
            "sub": str(user_id),
            "jti": str(jti),
            "exp": int((now + timedelta(seconds=self.refresh_ttl)).timestamp()),
            "iat": int(now.timestamp()),
            "type": "refresh",
        }
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return token, jti

    def verify_token(self, token: str, expected_type: str = "access") -> TokenPayload:
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            token_data = TokenPayload(**payload)
            if token_data.type != expected_type:
                raise ValueError(f"Invalid token type: expected {expected_type}, got {token_data.type}")
            return token_data
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
