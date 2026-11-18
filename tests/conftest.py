import os

os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
import redis.asyncio as redis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.redis import RedisContainer

from app.core.database import get_db
from app.main import app
from app.models.db_models import Base


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:14") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:latest") as redis_c:
        yield redis_c


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine(postgres_container):
    """Создает async-движок для тестовой БД и создвет таблицы."""
    url = postgres_container.get_connection_url()
    url = url.replace("postgresql+psycopg2", "postgresql+asyncpg")

    engine = create_async_engine(url, echo=False, poolclass=NullPool)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine  # ← обязательно верни engine!
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_session_factory(test_engine):
    """Фабрика тесетовых сессий на основе тестового движка."""
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def test_redis_client(redis_container):
    """Асинхронный Redis-клиент к тестовому контейнеру."""
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    client = redis.Redis(host=host, port=port, decode_responses=True)
    yield client


@pytest.fixture
def mock_gigachat():
    """Мок GigaChat, возвращающий фиксированный ответ."""
    mock = AsyncMock()

    fake_message = MagicMock()
    fake_message.content = "Это тестовый ответ от GigaChat"

    fake_choice = MagicMock()
    fake_choice.message = fake_message

    fake_response = MagicMock()
    fake_response.choices = [fake_choice]

    mock.achat.return_value = fake_response
    return mock


@pytest.fixture
def test_app(
    test_redis_client, mock_gigachat, test_session_factory, mock_kafka_producer
):
    """Тестовое приложение с подменёнными зависимостями."""

    async def override_get_db():  # ← замыкание!
        async with test_session_factory() as session:
            yield session

    app.state.redis = test_redis_client
    app.state.gigachat = mock_gigachat
    app.state.kafka_producer = mock_kafka_producer
    app.dependency_overrides[get_db] = override_get_db

    yield app

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(test_app):
    """HTTP-клиент для тестового приложения."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as client:
        yield client


import pytest
from sqlalchemy import text

from app.models.db_models import Model


@pytest_asyncio.fixture
async def test_model(test_session_factory):
    async with test_session_factory() as session:
        model = Model(name="test-model", description="Model for tests")
        session.add(model)
        await session.commit()
        await session.refresh(model)
        model_id = model.id
    return model_id


@pytest.fixture
def mock_kafka_producer():
    """Mok Kafka-producer"""
    mock = AsyncMock()
    mock.send = AsyncMock()
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    return mock


@pytest_asyncio.fixture(autouse=True)
async def clean_db(test_session_factory):
    yield
    async with test_session_factory() as session:
        await session.execute(
            text("TRUNCATE models, inference_logs RESTART IDENTITY CASCADE")
        )
        await session.commit()
