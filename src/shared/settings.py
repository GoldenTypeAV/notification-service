from typing import Any
from pydantic import PostgresDsn, RedisDsn, Field, model_validator
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    dsn: PostgresDsn | None = Field(default=None, validation_alias="dsn")

    user: str = "postgres"
    password: str = "postgres"
    host: str = "localhost"
    port: int = 5432
    db: str = "notifications"

    pool_size: int = 20
    max_overflow: int = 10
    echo: bool = False

    @model_validator(mode="before")
    @classmethod
    def assemble_db_connection(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        if data.get("dsn"):
            return data

        user = data.get("user", "postgres")
        password = data.get("password", "postgres")
        host = data.get("host", "localhost")
        port = data.get("port", 5432)
        db = data.get("db", "notifications")

        dsn = MultiHostUrl.build(
            scheme="postgresql+asyncpg",
            username=user,
            password=password,
            host=host,
            port=int(port),
            path=db,
        )

        data["dsn"] = dsn
        return data


class RedisSettings(BaseSettings):
    url: RedisDsn = "redis://localhost:6379/0"
    max_connections: int = 10

    host: str = "localhost"
    port: int = 6379

    @model_validator(mode="before")
    @classmethod
    def assemble_url(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        if data.get("url"):
            return data

        host = data.get("host", "localhost")
        port = data.get("port", 6379)

        dsn = MultiHostUrl.build(
            scheme="redis",
            host=host,
            port=int(port),
            path="0",
        )

        data["url"] = dsn
        return data


class KafkaSettings(BaseSettings):
    bootstrap_servers: str = "localhost:9092"
    group_id: str = "my-group"
    auto_offset_reset: str = "earliest"

    high_priority_topic: str = "notifications.high"
    normal_priority_topic: str = "notifications.normal"

    acks: str = "all"
    enable_idempotence: bool = True


class EmailProviderSettings(BaseSettings):
    provider: str = "smtp"
    host: str = "mailhog"
    port: int = 1025
    use_tls: bool = False
    from_email: str = "noreply@example.com"


class SMSProviderSettings(BaseSettings):
    provider: str = "mock"
    api_key: str = ""


class RetrySettings(BaseSettings):
    max_attempts: int = 3
    delays: list[int] = [5, 30, 120]  # seconds
    scheduler_interval_sec: int = 10
    scheduler_batch_size: int = 50
    run_scheduler: bool = True
    # Через сколько секунд QUEUED-запись считается застрявшей и переотправляется.
    stuck_after_sec: int = 60


class DedupSettings(BaseSettings):
    idempotency_ttl_sec: int = 24 * 60 * 60
    processing_lock_ttl_sec: int = 60
    history_cache_ttl_sec: int = 30


class Settings(BaseSettings):
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    worker_topic: str = "notifications.normal"

    env: str = "development"
    debug: bool = False

    db: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    kafka: KafkaSettings = KafkaSettings()
    email: EmailProviderSettings = EmailProviderSettings()
    sms: SMSProviderSettings = SMSProviderSettings()
    retry: RetrySettings = RetrySettings()
    dedup: DedupSettings = DedupSettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore"
    )

    def topic_for_priority(self, priority: str) -> str:
        if str(priority) == "high":
            return self.kafka.high_priority_topic
        return self.kafka.normal_priority_topic


settings = Settings()
