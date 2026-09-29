from typing import Optional
from fastapi import Header, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict
from app.core.config import settings
from app.core.logging import logger


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    email: Optional[str] = None
    role: str = "authenticated"


async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> AuthenticatedUser:
    """
    Validates the Supabase Bearer JWT token (S-1, S-2).
    Extracts the user 'sub' identifier.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split("Bearer ", 1)[1].strip()

    try:
        # Decode token using Supabase JWT secret or audience verification
        # Supabase signs access tokens with the project JWT secret
        payload = jwt.decode(
            token,
            settings.SUPABASE_ANON_KEY,
            algorithms=["HS256"],
            audience=settings.JWT_AUDIENCE,
            options={"verify_signature": False}
            if settings.ENVIRONMENT == "development"
            else {"verify_signature": True},
        )
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload missing subject identifier",
            )
        role: str = payload.get("role", "authenticated")
        email: Optional[str] = payload.get("email")

        return AuthenticatedUser(user_id=user_id, email=email, role=role)

    except JWTError as e:
        logger.warning(f"JWT verification failure: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_user_ownership(
    requested_user_id: str, current_user: AuthenticatedUser
) -> None:
    """
    Enforces S-3: Row-level authorization re-checked server-side on every request.
    Prevents cross-user access at the FastAPI routing layer.
    """
    if (
        current_user.user_id != requested_user_id
        and current_user.role != "service_role"
    ):
        logger.warning(
            f"Cross-user access attempt blocked: user {current_user.user_id} attempted access to resource of {requested_user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not have permission to access another user's resources",
        )
