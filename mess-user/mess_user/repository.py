from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mess_user.models.user import User


async def get_user(session: AsyncSession, user_id: str) -> Optional[User]:
    return (await session.scalars(select(User).filter(User.id == user_id))).first()


async def create_user(session: AsyncSession, username: str) -> User:
    user = User(username=username)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


async def delete_user(session: AsyncSession, user_id: str) -> None:
    user = await session.scalar(select(User).filter(User.id == user_id))
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
    return (await session.scalars(select(User).filter(User.id.in_(user_ids)))).all()
