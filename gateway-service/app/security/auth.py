from uuid import UUID

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth.jwt_utils import JWTService
from app.auth.service import AuthService
from app.config.dependencies import get_auth_service, get_jwt_service
from app.domain.auth_models import User

security = HTTPBearer(scheme_name="Bearer")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    auth_service: AuthService = Depends(get_auth_service),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt_service.verify_token(token, expected_type="access")
        user_id = UUID(payload.sub)
        user = await auth_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

