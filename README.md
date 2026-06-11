# Notification Service

Микросервис для массовых и транзакционных уведомлений (Email, SMS) с приоритизацией,
идемпотентностью, ретраями и контролем статусов доставки.

Стек: FastAPI, PostgreSQL, Redis, Kafka, SQLAlchemy 2.0, Alembic, Docker.

## Возможности

- Массовая и одиночная рассылка через REST API.
- Приоритизация: транзакционные уведомления (`high`) идут отдельным топиком и
  обрабатываются выделенным воркером, не конкурируя с маркетинговыми (`normal`).
- Статусы доставки: `queued`, `sent`, `delivered`, `dropped`.
- Идемпотентность запросов (ключ в теле запроса + уникальный индекс в БД + Redis).
- Гарантия доставки: персистентность в Kafka, `acks=all` + идемпотентный producer,
  ручной commit оффсета после обработки (at-least-once), повторы при сбоях шлюза.
- Дедупликация на уровне бизнес-логики (близко к exactly-once): статус-проверка
  плюс блокировка обработки в Redis.
- Кэш истории уведомлений в Redis.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

Поднимаются: PostgreSQL, Redis, Kafka, Mailhog, миграции, API и два воркера
(`worker` для `normal`, `worker-high` для `high`). Миграции применяются автоматически
сервисом `migrate` до старта приложения.

- API: `http://localhost:8000/api/v1`
- Swagger: `http://localhost:8000/docs`
- Mailhog (просмотр писем): `http://localhost:8025`

## API

Все маршруты под префиксом `/api/v1`.

### Подписчики и контакты

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/subscribers/` | Создать подписчика |
| GET | `/subscribers/` | Список подписчиков |
| GET | `/subscribers/{id}` | Получить подписчика |
| PATCH | `/subscribers/{id}` | Обновить `is_active` |
| DELETE | `/subscribers/{id}` | Удалить подписчика (каскадно с контактами) |
| POST | `/subscribers/{id}/contacts` | Добавить контакт |
| GET | `/subscribers/{id}/contacts` | Контакты подписчика |
| PUT | `/contacts/{contact_id}` | Обновить контакт |
| DELETE | `/contacts/{contact_id}` | Удалить контакт |

### Уведомления

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/notifications/single` | Уведомление одному подписчику |
| POST | `/notifications/bulk` | Массовая рассылка |
| GET | `/notifications/history/{subscriber_id}` | История и статусы подписчика |
| POST | `/admin/notifications/retry` | Перезапуск отброшенных (`dropped`) уведомлений |

### Пример

```http
POST /api/v1/notifications/bulk
Content-Type: application/json

{
  "channel": "email",
  "content": "Акция! Скидка 20%",
  "subscriber_ids": [1, 2, 3],
  "priority": "normal",
  "idempotency_key": "campaign-2026-06-11"
}
```

Ответ `202 Accepted`. Итоговый ключ идемпотентности формируется как
`{idempotency_key}:{subscriber_id}` — повторный запрос не создаёт дублей.

## Архитектура

```
        ┌─────────┐   high/normal   ┌──────────┐
client ─▶  API    ├───── Kafka ─────▶  Worker   ├──▶ Provider (SMTP / mock)
        └────┬────┘                 └────┬─────┘
             │                           │
        Postgres ◀──── статусы ──────────┘
             ▲                           ▲
           Redis (идемпотентность, блокировки, кэш)
```

- **API** — валидирует запрос, пишет уведомления в БД и публикует события в Kafka.
- **Worker** — читает свой топик, отправляет через провайдера, обновляет статус.
  Повторы при временных сбоях планируются в БД (`next_retry_at`).
- **Планировщик** (в воркере `normal`) — переотправляет в Kafka уведомления,
  готовые к повтору, и подстраховывает записи, не попавшие в брокер.
- **Redis** — ключи идемпотентности, блокировки обработки, кэш истории.

### Статусы

- `queued` — принято, ожидает отправки.
- `sent` — передано шлюзу.
- `delivered` — доставка подтверждена шлюзом.
- `dropped` — постоянная ошибка (нет контакта, отказ адреса, исчерпаны повторы).

## Локальная разработка

```bash
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"

# нужны поднятые Postgres/Redis/Kafka (например, из docker compose)
alembic upgrade head
uvicorn src.api.main:app --reload
python -m src.worker.main
```

## Тесты

```bash
pip install -e ".[dev]"
pytest tests/unit          # без внешних зависимостей
pytest tests/integration   # требует Docker (testcontainers поднимает Postgres)
```

Интеграционные тесты проверяют всю цепочку: приём сообщения воркером, вызов
провайдера и изменение статуса в БД, а также REST API подписчиков и историю.

## Конфигурация

Переменные окружения (см. `.env.example`), вложенные секции через `__`:

```ini
DB__HOST=db
REDIS__HOST=redis
KAFKA__BOOTSTRAP_SERVERS=kafka:9092
EMAIL__PROVIDER=smtp          # smtp | mock
SMS__PROVIDER=mock
RETRY__MAX_ATTEMPTS=3
RETRY__DELAYS=[5,30,120]
```

Полный список — в `src/shared/settings.py`.
