def test_postgres_starts(postgres_container):
    """Проверяем, что контейнер Postgres поднимается."""
    assert postgres_container is not None
    url = postgres_container.get_connection_url()
    assert "postgresql" in url
    print(f"Postgres URL: {url}")


def test_redis_starts(redis_container):
    """Проверяем, что контейнер Redis поднимается."""
    assert redis_container is not None
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    print(f"Redis: {host}:{port}")


async def test_tables_created(test_engine):
    """Проверяем, что таблицы создались в тестовой БД."""
    from sqlalchemy import text

    async with test_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
            )
        )
    tables = [row[0] for row in result.fetchall()]

    print(f"Tables: {tables}")
    assert "models" in tables
    assert "inference_logs" in tables


# async def override_get_db(test_session_factory):
#     """Замена get_db для тестов."""
#     async with test_session_factory() as session:
#         yield session


async def test_session_factory_creates_session(test_session_factory):
    """Проверяем , что фабрика создает рабочую сессию."""
    from sqlalchemy import text

    async with test_session_factory() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
