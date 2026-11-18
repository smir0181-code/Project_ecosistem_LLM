import asyncio
import json

from aiokafka import AIOKafkaConsumer


async def consume():
    consumer = AIOKafkaConsumer(
        "inference-events",
        bootstrap_servers="127.0.0.1:9092",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    await consumer.start()
    try:
        async for msg in consumer:
            print(f"Received:{msg.value}")
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(consume())
