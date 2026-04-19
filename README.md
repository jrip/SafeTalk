# SafeTalk

SafeTalk - backend-сервис для работы с ML-предсказаниями токсичности текста, балансом токенов и историей запросов.

## Стек

- Python 3.12
- FastAPI
- SQLAlchemy 2.x
- PostgreSQL / SQLite (локально)

## Быстрый запуск

### Локально

```bash
PYTHONPATH=. DATABASE_URL=sqlite:///./safetalk_local.db python -m uvicorn app.main:app --reload
```

Swagger UI: `http://127.0.0.1:8000/docs`

### Docker Compose

```bash
docker compose up -d --build
```

## Тесты

Сценарии ручного тестирования и краткий вывод для отчета вынесены в `TESTING_SCENARIOS.md`.

### Установка dev-зависимостей

```bash
python -m pip install -r app/requirements-dev.txt
```

### Запуск unit-тестов

```bash
python -m pytest tests/unit
```

### Запуск интеграционных тестов

```bash
python -m pytest tests/integration
```

### Запуск всех тестов

```bash
python -m pytest tests
```

### Запуск unit-тестов с coverage

```bash
python -m pytest tests --cov=app --cov-report=term
```

Что покрывается сейчас:

- unit-тесты лежат в `tests/unit`
- интеграционные тесты лежат в `tests/integration`
- unit-тестами покрываются сервисный слой, auth, error handlers и route-функции backend-модулей
- интеграционные тесты проверяют пользовательские backend-сценарии через HTTP (`register -> verify -> login`, баланс, ML-запросы, история)
- для подробного отчета по покрытию можно добавить `--cov-report=html`

Пример:

```bash
python -m pytest tests --cov=app --cov-report=term --cov-report=html
```

## Конфигурация

Используются переменные окружения:

- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DB_NAME`
- или единый `database_url`
- `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASS` 

Пример: `app/.env`.

## Архитектура

Каждый модуль разделен на слои:

- `routes.py` - HTTP-слой (FastAPI, Pydantic, коды ответов)
- `service.py` - бизнес-правила и orchestration между модулями
- `storage_sqlalchemy.py` - доступ к данным и SQLAlchemy-запросы
- `models.py` - ORM-модели и связи
- `types.py` - DTO для обмена между слоями

### Модули

- `app/modules/users` - регистрация, логин, профиль пользователя, базовая auth-логика
- `app/modules/billing` - баланс, пополнение, списание, журнал транзакций
- `app/modules/neural` - запуск ML-предикта, расчет стоимости, создание ML-задач
- `app/modules/history` - история запросов и операций пользователя
- `app/modules/telegram` - webhook-обработчик Telegram-бота (бот-логика в этом же сервисе)
- `app/modules/system` - технические health-check эндпоинты

### Базовые принципы

- Роуты валидируют вход и вызывают сервисы; бизнес-логика в `service.py`.
- Сервисы работают с доменными DTO из `types.py`, а не с HTTP-схемами и не с ORM-моделями наружу.
- Доступ к БД выполняется через `storage_sqlalchemy.py`.
- Доменные ошибки преобразуются в HTTP централизованно (`app/core/error_handlers.py`).

Подробные инженерные правила и DoD для новых эндпоинтов ведутся локально в `LLM_NOTES.local.md`.

## Единый формат ошибок

Глобальные обработчики в `app/core/error_handlers.py` возвращают JSON:

```json
{
  "error": "validation_error",
  "message": "Human-readable message",
  "details": {}
}
```

Типовые соответствия:

- `ValidationError` -> `400`
- `NotFoundError` -> `404`
- `InsufficientBalanceError` -> `409`
- `RequestValidationError` -> `422`

## REST API

Ниже зафиксирован текущий контракт HTTP API в формате reference.

| Method | Path | Purpose | Auth | Notes |
|---|---|---|---|---|
| `GET` | `/health` | Liveness probe приложения | No | Проверка, что процесс жив |
| `GET` | `/health/db` | Readiness probe БД | No | Проверка соединения с БД |
| `POST` | `/auth/register` | Регистрация пользователя | No | Создает пользователя и кошелек |
| `POST` | `/telegram/webhook` | Webhook Telegram-бота | Telegram Secret Token | Получает update от Telegram и обрабатывает команды внутри сервиса |
| `POST` | `/auth/verify-email` | Подтверждение email | No | Проверяет код подтверждения из mock-письма (в логах) |
| `POST` | `/auth/login` | Логин пользователя | No | Возвращает `access_token`; вход только после verify-email |
| `GET` | `/users/{user_id}` | Профиль пользователя | Bearer | Доступ только к своему `user_id` |
| `PATCH` | `/users/{user_id}` | Обновление профиля | Bearer | Доступ только к своему `user_id` |
| `GET` | `/balance/{user_id}` | Текущий баланс | Bearer | Доступ только к своему `user_id` |
| `POST` | `/balance/{user_id}/topup` | Пополнение баланса | Bearer (admin) | Только admin; можно пополнять баланс любого пользователя |
| `POST` | `/balance/{user_id}/spend` | Списание токенов | Bearer (admin) | Только admin; можно списывать у любого пользователя |
| `GET` | `/balance/{user_id}/ledger` | История транзакций | Bearer | Доступ только к своему `user_id` |
| `POST` | `/predict` | Создать ML-задачу | Bearer | `user_id` берется из токена; списывает токены и пишет историю |
| `GET` | `/history/{user_id}` | История ML-запросов | Bearer | Доступ только к своему `user_id` |

Профиль пользователя хранится в `users`, а способы входа (email/telegram) — в `user_identities`.

Параметры верификации email настраиваются через env:
- `EMAIL_VERIFICATION_TTL_SECONDS` (по умолчанию `3600`)
- `EMAIL_VERIFICATION_MAX_ATTEMPTS` (по умолчанию `10`)

Для Telegram webhook нужны env-параметры:
- `TELEGRAM_BOT_TOKEN` - токен бота для вызова Telegram Bot API (`sendMessage`)
- `TELEGRAM_WEBHOOK_SECRET_TOKEN` - секрет, который Telegram шлет в `X-Telegram-Bot-Api-Secret-Token`
- без корректного webhook secret -> `401`, если secret не настроен -> `503`

