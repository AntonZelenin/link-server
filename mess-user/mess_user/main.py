from collections import defaultdict

import httpx
from fastapi import FastAPI, status, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from result import Ok, Err

from mess_user import repository, helpers, settings, schemas
from mess_user.deps import DBSessionDep
from mess_user.helpers import user
from mess_user.models.user import User
from mess_user.schemas import UserRegisterData, GetUsersByIdsRequest, SearchUsersResponse

app = FastAPI()


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


@app.post('/api/user/v1/users')
async def register(user_data: UserRegisterData, session: DBSessionDep):
    if await repository.username_exists(session, user_data.username):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={'errors': {'username': 'This username is already taken'}},
        )

    user_ = await repository.create_user(session, user_data.username)

    try:
        match helpers.user.create_user_in_auth(user_.id, user_.username, user_data.password):
            case Ok(_):
                return await login(user_data)
            case Err(message):
                # todo it always returns 400, even if auth is down and it should be 500
                await repository.delete_user(session, user_.id)
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=message,
                )
    except Exception as e:
        await repository.delete_user(session, user_.id)
        raise e


async def login(register_data: UserRegisterData):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.get_settings().auth_url + '/api/auth/v1/login',
            json={"username": register_data.username, "password": register_data.password}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Login service failed")
        return response.json()


@app.get('/api/user/v1/users')
async def find_users(
        username: str,
        session: DBSessionDep,
        user_: User = Depends(helpers.user.get_current_active_user),
) -> SearchUsersResponse:
    users = await repository.search_users(session, username, exclude_username=user_.username)
    return SearchUsersResponse(users=[schemas.User(id=u.id, username=u.username) for u in users])


@app.post('/api/user/v1/users/batch-query')
async def get_users_by_ids(req: GetUsersByIdsRequest, session: DBSessionDep) -> SearchUsersResponse:
    if len(req.user_ids) == 0:
        return SearchUsersResponse(users=[])

    db_users = await repository.get_users(session, req.user_ids)
    return SearchUsersResponse(users=[schemas.User(id=db_user.id, username=db_user.username) for db_user in db_users])
