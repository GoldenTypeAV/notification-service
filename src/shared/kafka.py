from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from src.shared.settings import settings
import json

# Producer
producer: AIOKafkaProducer | None = None

async def init_kafka_producer():
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka.bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode(),
    )
    await producer.start()

async def close_kafka_producer():
    if producer:
        await producer.stop()

async def get_producer() -> AIOKafkaProducer:
    return producer

# Consumer
def create_consumer(*topics):
    return AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.kafka.bootstrap_servers,
        group_id=settings.kafka.group_id,
        auto_offset_reset=settings.kafka.auto_offset_reset,
        value_deserializer=lambda m: json.loads(m.decode()),
    )