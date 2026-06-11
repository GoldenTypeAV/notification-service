from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from enum import Enum
from src.shared.settings import settings
import json


class KafkaTopic(str, Enum):
    HIGH_PRIORITY = "notifications.high"
    NORMAL_PRIORITY = "notifications.normal"


def _build_producer() -> AIOKafkaProducer:
    return AIOKafkaProducer(
        bootstrap_servers=settings.kafka.bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode(),
        acks=settings.kafka.acks,
        enable_idempotence=settings.kafka.enable_idempotence,
    )


producer: AIOKafkaProducer | None = None


async def init_kafka_producer() -> AIOKafkaProducer:
    global producer
    producer = _build_producer()
    await producer.start()
    return producer


async def close_kafka_producer() -> None:
    global producer
    if producer:
        await producer.stop()
        producer = None


async def get_producer() -> AIOKafkaProducer:
    return producer


async def create_producer() -> AIOKafkaProducer:
    """Отдельный producer для случаев, где общий недоступен (скрипты, тесты)."""
    p = _build_producer()
    await p.start()
    return p


def create_consumer(*topics, group_id: str | None = None) -> AIOKafkaConsumer:
    return AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.kafka.bootstrap_servers,
        group_id=group_id or settings.kafka.group_id,
        auto_offset_reset=settings.kafka.auto_offset_reset,
        enable_auto_commit=False,  # коммит вручную после обработки
        value_deserializer=lambda m: json.loads(m.decode()),
    )
