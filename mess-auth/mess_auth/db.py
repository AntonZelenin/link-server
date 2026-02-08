from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from mess_auth import settings

engine = create_async_engine(settings.get_settings().async_db_url)
async_session = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
