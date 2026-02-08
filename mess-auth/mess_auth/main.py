from collections import defaultdict
from datetime import timedelta
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from jose import JWTError, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from mess_auth import repository, schemas, utils, settings, logger
from mess_auth.db import get_session
from mess_auth.models.user import User
from mess_auth.schemas import RefreshTokenRequest, LoginData, LoginRequest

logger_ = logger.get_logger(__name__, stdout=True)

app = FastAPI()


async def authenticate_by_creds(session: AsyncSession, username: str, password: str) -> Optional[User]:
    user = await repository.get_user_by_username(session, username)
    if user and utils.is_valid_password(password, user.hashed_password):
        return user

    return None


@app.exception_handler(RequestValidationError)
async def custom_form_validation_error(_, exc):
    reformatted_message = defaultdict(list)
    for pydantic_error in exc.errors():
        loc, msg = pydantic_error["loc"], pydantic_error["msg"]
        filtered_loc = loc[1:] if loc[0] in ("body", "query", "path") else loc
        field_string = ".".join(filtered_loc)  # nested fields with dot-notation
        reformatted_message[field_string].append(msg)

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(
            {"errors": reformatted_message}
        ),
    )


# todo make sure user is active everywhere
@app.post("/api/auth/v1/login")
async def login(
        request: LoginRequest,
        session: AsyncSession = Depends(get_session),
) -> LoginData:
    user = await authenticate_by_creds(session, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = utils.create_jwt(
        claims={"user-id": user.user_id, "username": user.username},
        expires_delta=timedelta(minutes=settings.get_settings().access_token_expire_minutes),
    )
    refresh_token = utils.create_jwt(
        claims={"user-id": user.user_id},
        expires_delta=timedelta(minutes=settings.get_settings().refresh_token_expire_minutes),
    )
    await repository.create_refresh_token(session, user.user_id, refresh_token)

    return LoginData(access_token=access_token, refresh_token=refresh_token, token_type="bearer", user_id=user.user_id)


# todo duplicates
# todo I need a mechanism to remove old refresh tokens from the database
@app.post("/api/auth/v1/refresh-token")
async def refresh_token_(
        refresh_token_request: RefreshTokenRequest, session: AsyncSession = Depends(get_session),
) -> LoginData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = utils.decode_access_token(refresh_token_request.refresh_token)
    except ExpiredSignatureError:
        logger_.info("Expired refresh token")
        raise credentials_exception
    except JWTError:
        logger_.info("Invalid refresh token")
        raise credentials_exception

    user_id = payload.get("user-id")
    if user_id is None:
        logger_.info("`user-id` field is not found in refresh token payload")
        raise credentials_exception

    user = await repository.get_user(session, user_id)
    if user is None:
        logger_.info("User from the refresh token not found")
        raise credentials_exception

    if not await repository.refresh_token_exists(session, user_id, refresh_token_request.refresh_token):
        logger_.info("Refresh token does not match the one in the database")
        raise credentials_exception

    access_token = utils.create_jwt(
        claims={"user-id": user.user_id, "username": user.username},
        expires_delta=timedelta(minutes=settings.get_settings().access_token_expire_minutes),
    )
    refresh_token_request = utils.create_jwt(
        claims={"user-id": user.user_id},
        expires_delta=timedelta(minutes=settings.get_settings().refresh_token_expire_minutes),
    )

    await repository.update_refresh_token(session, user_id, refresh_token_request)

    return LoginData(
        access_token=access_token,
        refresh_token=refresh_token_request,
        token_type="bearer",
        user_id=user.user_id
    )


@app.post("/api/auth/v1/logout")
async def logout(
        refresh_token_request: RefreshTokenRequest, session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        payload = utils.decode_access_token(refresh_token_request.refresh_token)
    except ExpiredSignatureError:
        logger_.info("Expired refresh token")
        return {"message": "Expired refresh token"}
    except JWTError:
        logger_.info("Invalid refresh token")
        return {"message": "Invalid refresh token"}

    user_id = payload.get("user-id")
    if user_id is None:
        logger_.info("`user-id` field is not found in refresh token payload")
        return {"message": "Could not validate credentials"}

    user = await repository.get_user(session, user_id)
    if user is None:
        logger_.info("User from the refresh token not found")
        return {"message": "Could not validate credentials"}

    await repository.delete_refresh_token(session, user_id, refresh_token_request.refresh_token)

    return {"message": "Logged out successfully"}


@app.post("/api/auth/v1/users")
async def create_user(user: schemas.User, session: AsyncSession = Depends(get_session)) -> dict:
    if await repository.get_user_by_username(session, user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )

    await repository.create_user(session, user.user_id, user.username, utils.get_password_hash(user.password))

    return {"message": "User created successfully"}
