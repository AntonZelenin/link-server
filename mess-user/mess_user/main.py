import logging
from collections import defaultdict
from datetime import timedelta
from typing import Optional

from fastapi import FastAPI, status, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from jose import JWTError, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession

from mess_user import repository, schemas, utils, settings
from mess_user.deps import DBSessionDep, get_current_active_user
from mess_user.models.user import User
from mess_user.schemas import (
    UserRegisterData, GetUsersByIdsRequest, SearchUsersResponse,
    LoginRequest, LoginData, RefreshTokenRequest,
)

logger = logging.getLogger(__name__)

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
        loc, msg = pydantic_error['loc'], pydantic_error['msg']
        filtered_loc = loc[1:] if loc[0] in ('body', 'query', 'path') else loc
        field_string = '.'.join(filtered_loc)  # nested fields with dot-notation
        reformatted_message[field_string].append(msg)

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(
            {'errors': reformatted_message}
        ),
    )


# --- User endpoints ---

@app.post('/api/user/v1/users')
async def register(user_data: UserRegisterData, session: DBSessionDep):
    if await repository.username_exists(session, user_data.username):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={'errors': {'username': 'This username is already taken'}},
        )

    hashed_password = utils.get_password_hash(user_data.password)
    user_ = await repository.create_user(session, user_data.username, hashed_password)

    access_token = utils.create_jwt(
        claims={"user-id": user_.user_id, "username": user_.username},
        expires_delta=timedelta(minutes=settings.get_settings().access_token_expire_minutes),
    )
    refresh_token = utils.create_jwt(
        claims={"user-id": user_.user_id},
        expires_delta=timedelta(minutes=settings.get_settings().refresh_token_expire_minutes),
    )
    await repository.create_refresh_token(session, user_.user_id, refresh_token)

    return LoginData(
        access_token=access_token, refresh_token=refresh_token,
        token_type="bearer", user_id=user_.user_id,
    )


@app.get('/api/user/v1/users')
async def find_users(
        username: str,
        session: DBSessionDep,
        user_: User = Depends(get_current_active_user),
) -> SearchUsersResponse:
    users = await repository.search_users(session, username, exclude_username=user_.username)
    return SearchUsersResponse(users=[schemas.User(user_id=u.user_id, username=u.username) for u in users])


@app.post('/api/user/v1/users/batch-query')
async def get_users_by_ids(req: GetUsersByIdsRequest, session: DBSessionDep) -> SearchUsersResponse:
    if len(req.user_ids) == 0:
        return SearchUsersResponse(users=[])

    db_users = await repository.get_users(session, req.user_ids)
    return SearchUsersResponse(users=[schemas.User(user_id=db_user.user_id, username=db_user.username) for db_user in db_users])


# --- Auth endpoints ---

# todo make sure user is active everywhere
@app.post("/api/auth/v1/login")
async def login(request: LoginRequest, session: DBSessionDep) -> LoginData:
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
        refresh_token_request: RefreshTokenRequest, session: DBSessionDep,
) -> LoginData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = utils.decode_access_token(refresh_token_request.refresh_token)
    except ExpiredSignatureError:
        logger.info("Expired refresh token")
        raise credentials_exception
    except JWTError:
        logger.info("Invalid refresh token")
        raise credentials_exception

    user_id = payload.get("user-id")
    if user_id is None:
        logger.info("`user-id` field is not found in refresh token payload")
        raise credentials_exception

    user = await repository.get_user(session, user_id)
    if user is None:
        logger.info("User from the refresh token not found")
        raise credentials_exception

    if not await repository.refresh_token_exists(session, user_id, refresh_token_request.refresh_token):
        logger.info("Refresh token does not match the one in the database")
        raise credentials_exception

    access_token = utils.create_jwt(
        claims={"user-id": user.user_id, "username": user.username},
        expires_delta=timedelta(minutes=settings.get_settings().access_token_expire_minutes),
    )
    new_refresh_token = utils.create_jwt(
        claims={"user-id": user.user_id},
        expires_delta=timedelta(minutes=settings.get_settings().refresh_token_expire_minutes),
    )

    await repository.update_refresh_token(session, user_id, new_refresh_token)

    return LoginData(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user_id=user.user_id,
    )


@app.post("/api/auth/v1/logout")
async def logout(
        refresh_token_request: RefreshTokenRequest, session: DBSessionDep,
) -> dict:
    try:
        payload = utils.decode_access_token(refresh_token_request.refresh_token)
    except ExpiredSignatureError:
        logger.info("Expired refresh token")
        return {"message": "Expired refresh token"}
    except JWTError:
        logger.info("Invalid refresh token")
        return {"message": "Invalid refresh token"}

    user_id = payload.get("user-id")
    if user_id is None:
        logger.info("`user-id` field is not found in refresh token payload")
        return {"message": "Could not validate credentials"}

    user = await repository.get_user(session, user_id)
    if user is None:
        logger.info("User from the refresh token not found")
        return {"message": "Could not validate credentials"}

    await repository.delete_refresh_token(session, user_id, refresh_token_request.refresh_token)

    return {"message": "Logged out successfully"}
