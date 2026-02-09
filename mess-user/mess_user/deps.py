from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from mess_user import repository
from mess_user.db import get_db_session
from mess_user.models.user import User

DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


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
