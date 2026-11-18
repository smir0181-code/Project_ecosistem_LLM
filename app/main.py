import json
import logging
from contextlib import asynccontextmanager

import redis.asyncio as redis
from aiokafka import AIOKafkaProducer
from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from gigachat import GigaChat
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import GIGACHAT_CREDENTIALS
from app.core.database import get_db, init_db
from app.core.logging import setup_logging
from app.routers import generate

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.Redis(host="localhost", port=6380, decode_responses=True)
    app.state.gigachat = GigaChat(
        credentials=GIGACHAT_CREDENTIALS,
        scope="GIGACHAT_API_PERS",
        verify_ssl_certs=False,  # TODO: включить в prod
        model="GigaChat-2-Pro",
    )
    app.state.kafka_producer = AIOKafkaProducer(
        bootstrap_servers="127.0.0.1:9092",
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    try:
        await app.state.kafka_producer.start()
        logger.info("Kafka producer started")
    except Exception:  # noqa: BLE001 — Kafka is best-effort, app must start
        logger.warning("Kafka unavailable — events will not be published")
        app.state.kafka_producer = None

    try:
        await init_db()
        yield
    finally:
        if app.state.kafka_producer is not None:
            try:
                await app.state.kafka_producer.stop()
                logger.info("Kafka producer stopped")
            except Exception:
                logger.exception("Failed to stop Kafka producer")
        try:
            await app.state.redis.aclose()
        except Exception:
            logger.exception("Failed to close Redis")
        try:
            await app.state.gigachat.close()
        except Exception:
            logger.exception("Failed to close GigaChat")


app = FastAPI(lifespan=lifespan)
app.include_router(generate.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": exc.errors(), "body": exc.body},
    )


@app.get("/ping-db")
async def check_db(session: AsyncSession = Depends(get_db)):  # noqa: B008
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}
