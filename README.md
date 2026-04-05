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
| `POST` | `/auth/login` | Логин пользователя | No | Сейчас заглушка, возвращает `501` |
| `GET` | `/users/{user_id}` | Профиль пользователя | No* | Сейчас принимает `user_id` в URL |
| `PATCH` | `/users/{user_id}` | Обновление профиля | No* | Сейчас принимает `user_id` в URL |
| `GET` | `/balance/{user_id}` | Текущий баланс | No* | Сейчас принимает `user_id` в URL |
| `POST` | `/balance/{user_id}/topup` | Пополнение баланса | No* | Возвращает обновленный баланс |
| `POST` | `/balance/{user_id}/spend` | Списание токенов | No* | При нехватке средств -> `409` |
| `GET` | `/balance/{user_id}/ledger` | История транзакций | No* | Новые записи сверху |
| `POST` | `/predict` | Создать ML-задачу | No* | Списывает токены и пишет историю |
| `GET` | `/history/{user_id}` | История ML-запросов | No* | По пользователю |

`No*` означает, что текущая версия API еще не переведена на auth-context (`current user`) и использует `user_id` из пути/тела запроса.

