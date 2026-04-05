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
- `app/modules/telegram` - отдельный API-слой для Telegram-сценариев (регистрация/вход бота)
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
| `POST` | `/telegram/register` | Старт Telegram-онбординга | No | Принимает `telegram_id`, создает/находит пользователя, возвращает `status` (`need_email`/`ready`) без токена |
| `POST` | `/telegram/bind-email` | Привязка email к Telegram-пользователю | No | Создает/проверяет email-identity и отправляет mock-код верификации |
| `POST` | `/telegram/complete` | Завершение входа из Telegram | No | Выдает `access_token` только если email уже подтвержден |
| `POST` | `/auth/verify-email` | Подтверждение email | No | Проверяет код подтверждения из mock-письма (в логах) |
| `POST` | `/auth/login` | Логин пользователя | No | Возвращает `access_token`; вход только после verify-email |
| `GET` | `/users/{user_id}` | Профиль пользователя | Bearer | Доступ только к своему `user_id` |
| `PATCH` | `/users/{user_id}` | Обновление профиля | Bearer | Доступ только к своему `user_id` |
| `GET` | `/balance/{user_id}` | Текущий баланс | Bearer | Доступ только к своему `user_id` |
| `POST` | `/balance/{user_id}/topup` | Пополнение баланса | Bearer | Возвращает обновленный баланс |
| `POST` | `/balance/{user_id}/spend` | Списание токенов | Bearer | При нехватке средств -> `409` |
| `GET` | `/balance/{user_id}/ledger` | История транзакций | Bearer | Новые записи сверху |
| `POST` | `/predict` | Создать ML-задачу | Bearer | `user_id` берется из токена; списывает токены и пишет историю |
| `GET` | `/history/{user_id}` | История ML-запросов | Bearer | Доступ только к своему `user_id` |

Профиль пользователя хранится в `users`, а способы входа (email/telegram) — в `user_identities`.

Параметры верификации email настраиваются через env:
- `EMAIL_VERIFICATION_TTL_SECONDS` (по умолчанию `3600`)
- `EMAIL_VERIFICATION_MAX_ATTEMPTS` (по умолчанию `10`)

