from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mess_user.models.token import RefreshToken
from mess_user.models.user import User


async def get_user(session: AsyncSession, user_id: str) -> Optional[User]:
    return (await session.scalars(select(User).filter(User.user_id == user_id))).first()


async def get_user_by_username(session: AsyncSession, username: str) -> Optional[User]:
    return (await session.scalars(select(User).filter(User.username == username))).first()


async def create_user(session: AsyncSession, username: str, hashed_password: str) -> User:
    user = User(username=username, hashed_password=hashed_password)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


async def delete_user(session: AsyncSession, user_id: str) -> None:
    user = await session.scalar(select(User).filter(User.user_id == user_id))
    await session.delete(user)
    await session.commit()


async def username_exists(session: AsyncSession, username: str) -> bool:
    return (await session.scalars(select(User).filter(User.username == username))).first() is not None


async def search_users(
        session: AsyncSession,
        username_like: str,
        limit: int = 20,
        *,
        exclude_username: Optional[str] = None,
) -> Sequence[User]:
    query = select(User).filter(User.username.like(f"%{username_like}%")).limit(limit)
    if exclude_username:
        query = query.filter(User.username != exclude_username)

    return (await session.scalars(query)).all()


async def get_users(session: AsyncSession, user_ids: list[str]) -> Sequence[User]:
    return (await session.scalars(select(User).filter(User.user_id.in_(user_ids)))).all()


async def refresh_token_exists(session: AsyncSession, user_id: str, token: str) -> bool:
    return (
        await session.scalars(
            select(RefreshToken.token).filter(RefreshToken.user_id == user_id, RefreshToken.token == token)
        )
    ).first() is not None


async def create_refresh_token(session: AsyncSession, user_id: str, refresh_token: str) -> RefreshToken:
    token = RefreshToken(user_id=user_id, token=refresh_token)
    session.add(token)
    await session.commit()
    await session.refresh(token)

    return token


# todo if multiple devices are used they'll break each other tokens
async def update_refresh_token(session: AsyncSession, user_id: str, new_refresh_token: str) -> RefreshToken:
    refresh_token = (await session.scalars(select(RefreshToken).filter(RefreshToken.user_id == user_id))).first()

    if refresh_token is None:
        return await create_refresh_token(session, user_id, new_refresh_token)

    refresh_token.token = new_refresh_token
    await session.commit()
    await session.refresh(refresh_token)

    return refresh_token


async def delete_refresh_token(session: AsyncSession, user_id: str, token: str) -> None:
    refresh_token = (
        await session.scalars(select(RefreshToken).filter(RefreshToken.user_id == user_id, RefreshToken.token == token))
    ).first()

    if refresh_token is not None:
        await session.delete(refresh_token)
        await session.commit()
