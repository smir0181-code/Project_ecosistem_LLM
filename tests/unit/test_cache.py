from app.core.cache import get_cache_key
from app.models.schemas import GenerateRequest


def test_cache_key_format():
    """Проверяем, что ключ формируется по шаблону."""
    request = GenerateRequest(
        model_id=1, prompt="привет", temperature=0.7, max_tokens=100
    )
    key = get_cache_key(request)

    assert key.startswith("llm:1:")


def test_cache_key_contains_temperature_and_max_tokens():
    """Проверяем, что параметры попадают в ключ."""
    request = GenerateRequest(
        model_id=1, prompt="hello", temperature=0.5, max_tokens=200
    )
    key = get_cache_key(request)

    assert ":0.5:" in key
    assert key.endswith(":200")


def test_same_request_same_key():
    """Одинаковые запросы дают одинаковый ключ."""
    request1 = GenerateRequest(
        model_id=1, prompt="привет", temperature=0.7, max_tokens=100
    )
    request2 = GenerateRequest(
        model_id=1, prompt="привет", temperature=0.7, max_tokens=100
    )

    assert get_cache_key(request1) == get_cache_key(request2)


def test_different_prompt_different_key():
    """Разные model_id дают разные ключи."""
    request1 = GenerateRequest(model_id=1, prompt="by", temperature=0.7, max_tokens=100)
    request2 = GenerateRequest(
        model_id=1, prompt="привет", temperature=0.7, max_tokens=100
    )

    assert get_cache_key(request1) != get_cache_key(request2)


def test_different_model_id_different_key():
    """Разные model_id ключи кеша различаются"""
    request1 = GenerateRequest(
        model_id=1, prompt="привет", temperature=0.7, max_tokens=100
    )
    request2 = GenerateRequest(
        model_id=2, prompt="привет", temperature=0.7, max_tokens=100
    )

    assert get_cache_key(request1) != get_cache_key(request2)


def test_cache_key_hash_not_equal_prompt():
    """Ключ не должен равен в промпт в открвтом виде"""
    request = GenerateRequest(
        model_id=1, prompt="secret test", temperature=0.7, max_tokens=100
    )
    key = get_cache_key(request)
    assert "secret" not in key
    assert "test" not in key
    # import hashlib
    # expected_hash=hashlib.md5("secret test".encode()).hexdigest()
    # assert expected_hash in key


def test_empty_prompt_no_crash():
    """Запрос без промта"""
    request = GenerateRequest(model_id=1, prompt="", temperature=0.7, max_tokens=100)
    key = get_cache_key(request)
    assert key.startswith("llm")
