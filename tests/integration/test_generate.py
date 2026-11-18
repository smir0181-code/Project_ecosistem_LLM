async def test_generate_returns_200(
    async_client, test_model, mock_gigachat, mock_kafka_producer, clean_db
):

    response = await async_client.post(
        "/v1/generate/",
        json={
            "model_id": test_model,
            "prompt": "привет",
            "temperature": 0.7,
            "max_tokens": 100,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["model_id"] == test_model
    assert data["response"] == "Это тестовый ответ от GigaChat"
    mock_gigachat.achat.assert_awaited_once()
    mock_kafka_producer.send.assert_awaited_once()


async def test_generate_uses_cache(
    async_client, test_model, mock_gigachat, mock_kafka_producer
):
    payload = {
        "model_id": test_model,
        "prompt": "какая погода",
        "temperature": 0.7,
        "max_tokens": 100,
    }

    r1 = await async_client.post("/v1/generate/", json=payload)
    r2 = await async_client.post("/v1/generate/", json=payload)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["response"] == r2.json()["response"]
    # ключевой ассерт: второй запрос обслужен из Redis, GigaChat не дёрнут повторно
    mock_gigachat.achat.assert_awaited_once()
