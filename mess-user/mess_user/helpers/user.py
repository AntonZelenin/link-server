import requests
from fastapi import status, Header, HTTPException
from result import Result, Ok, Err

from mess_user import repository, settings
from mess_user.main import DBSessionDep
from mess_user.models.user import User


def create_user_in_auth(user_id: str, username: str, password: str) -> Result[bool, dict]:
    try:
        res = requests.post(
            # todo it depends on auth api route, I guess provide it from outside
            f"{settings.get_settings().auth_url}/api/auth/v1/users",
            json={
                "user_id": user_id,
                "username": username,
                "password": password,
            },
        )
        res.raise_for_status()

        return Ok(True)
    except requests.HTTPError as e:
        if e.response.status_code == 400:
            return Err(e.response.json())
        return Err({
            'errors': {
                'auth_error': [e.response],
            },
        })
    except Exception as e:
        return Err({
            'errors': {
                'exception': [str(e)],
            },
        })


# todo do I need user from db? auth checks everything and provides user_id, maybe I can only work with it
async def get_current_active_user(session: DBSessionDep, x_user_id: str = Header(None)) -> User:
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    user = await repository.get_user(session, x_user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    return user
