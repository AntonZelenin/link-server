from datetime import timedelta, timezone, datetime

from jose import jwt
from passlib.context import CryptContext

from mess_auth import constants, settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def is_valid_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_jwt(claims: dict, expires_delta: timedelta, headers: dict = None) -> str:
    to_encode = claims.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + expires_delta

    headers = headers or {}
    headers['kid'] = settings.get_settings().jwt_kid

    return jwt.encode(
        claims=to_encode,
        key=settings.get_settings().jwt_secret_key,
        algorithm=constants.ALGORITHM,
        headers=headers,
    )


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.get_settings().jwt_secret_key, algorithms=[constants.ALGORITHM])
