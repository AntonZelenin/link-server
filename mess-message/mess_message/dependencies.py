from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from mess_message import db
from mess_message.cache.cache import Cacher, RepositoryContextManager
from mess_message.chat_provider import ChatProvider
from mess_message.repository import Repository


async def get_session() -> AsyncSession:
    async with db.async_session() as session:
        yield session


def get_repository(session: AsyncSession = Depends(get_session)) -> Repository:
    return Repository(session)


async def get_cacher() -> Cacher:
    async with RepositoryContextManager() as repository:
        yield repository


def get_chat_provider(
        repository: Repository = Depends(get_repository),
        cacher: Cacher = Depends(get_cacher),
) -> ChatProvider:
    return ChatProvider(repository, cacher)
