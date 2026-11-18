import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cache_key, get_cached_response, set_cached_response
from app.core.database import get_db
from app.models.db_models import InferenceLog, Model
from app.models.schemas import GenerateRequest, GenerateResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/generate", tags=["generate"])


@router.post("/", response_model=GenerateResponse)
async def generate(
    generate_req: GenerateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),  # noqa: B008
):
    await asyncio.sleep(0.2)  # задержка для демо; убрать, если не нужна

    key = get_cache_key(generate_req)
    redis_client = request.app.state.redis

    try:
        cached = await get_cached_response(redis_client, key)
        if cached is not None:
            return GenerateResponse(response=cached, model_id=generate_req.model_id)
    except Exception as e:  # noqa: BLE001 — best-effort cache
        logger.warning("Redis read error: %s", e)

    model_exists = await session.get(Model, generate_req.model_id)
    if model_exists is None:
        raise HTTPException(
            status_code=404,
            detail=f"Model with id {generate_req.model_id} not found",
        )

    try:
        gigachat_client = request.app.state.gigachat
        response = await gigachat_client.achat(generate_req.prompt)
        ai_response = response.choices[0].message.content
    except Exception as e:
        logger.error("GigaChat error: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"GigaChat service unavailable: {e!s}",
        ) from e

    try:
        await set_cached_response(redis_client, key, ai_response, ttl=3600)
    except Exception as e:  # noqa: BLE001
        logger.warning("Redis write error: %s", e)

    log_entry = InferenceLog(
        model_id=generate_req.model_id,
        prompt=generate_req.prompt,
        response=ai_response,
        temperature=generate_req.temperature,
        tokens_used=0,
    )
    session.add(log_entry)
    await session.commit()

    producer = request.app.state.kafka_producer
    if producer is None:
        logger.debug("Kafka producer not configured, skipping event")
    else:
        try:
            event_data = {
                "model_id": generate_req.model_id,
                "prompt": generate_req.prompt,
                "response": ai_response,
                "temperature": generate_req.temperature,
                "tokens_used": 0,
                "timestamp": str(datetime.now()),
            }
            await producer.send("inference-events", value=event_data)
            logger.info("Message sent to Kafka")
        except Exception as e:  # noqa: BLE001
            logger.warning("Kafka send error: %s", e)

    return GenerateResponse(response=ai_response, model_id=generate_req.model_id)
