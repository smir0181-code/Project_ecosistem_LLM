import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.db_models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/llm_db"
)
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() in ("1", "true", "yes")

async_engine = create_async_engine(DATABASE_URL, echo=SQL_ECHO)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
