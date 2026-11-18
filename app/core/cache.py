import hashlib

from app.models.schemas import GenerateRequest


def get_cache_key(request: GenerateRequest) -> str:
    prompt_hash = hashlib.md5(request.prompt.encode()).hexdigest()
    return f"llm:{request.model_id}:{prompt_hash}:{request.temperature}:{request.max_tokens}"


async def get_cached_response(redis_client, key: str) -> str | None:
    return await redis_client.get(key)


async def set_cached_response(
    redis_client, key: str, response: str, ttl: int = 3600
) -> None:
    await redis_client.set(key, response, ex=ttl)
