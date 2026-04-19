# SafeTalk

SafeTalk - backend-сервис для работы с ML-предсказаниями токсичности текста, балансом токенов и историей запросов.

## Что умеет проект

- регистрация пользователя и подтверждение email
- авторизация и получение профиля
- пополнение баланса токенов
- запуск ML-предсказания токсичности текста
- просмотр истории запросов и результатов
- админские операции: просмотр пользователей, изменение профиля, управление балансом
- админская аналитика: статистика, история операций и просмотр ML-задач
- Telegram webhook для интеграции с ботом

## Стек

- Python 3.12
- FastAPI
- SQLAlchemy 2.x
- PostgreSQL / SQLite (локально)
- RabbitMQ
- React + TypeScript
- Vite
- Docker Compose
- Nginx

## Запуск

Все команды из корня репозитория. Таблицы в БД создаёт только Alembic: сначала поднимите БД, прогоните миграцию, потом запускайте `app` и `ml-worker` (иначе API и воркер могут падать на запросах к БД).

В `docker-compose.yml` в контейнер смонтированы `./app`, `./ml-worker`, `./alembic` и `alembic.ini`: новый код и файлы миграций на хосте видны без пересборки образа, пока не менялись `Dockerfile` или `requirements.txt` у соответствующего сервиса.

1. Создайте `app/.env` по образцу `app/.env.example`.

2. Соберите образы `app`, `ml-worker`, `web-proxy` и поднимите PostgreSQL и RabbitMQ (без `app`, `ml-worker` и `web-proxy`):

```bash
docker compose build app ml-worker web-proxy
docker compose up -d database rabbitmq
```

3. Примените миграции (одноразовый контейнер из того же образа `app`, Python на хосте не нужен):

```bash
docker compose run --rm app python -m alembic upgrade head
```

4. Поднимите приложение, воркеры и nginx:

```bash
docker compose up -d app ml-worker web-proxy
```

5. Откройте в браузере:

- `http://127.0.0.1/` - статическая страница проекта
- `http://127.0.0.1/dashboard/` - личный кабинет / frontend
- `http://127.0.0.1/docs` - Swagger UI
- `http://127.0.0.1/docs-public` - публичная документация
- `http://127.0.0.1/health` - проверка, что приложение запущено
- `http://127.0.0.1:15672` - RabbitMQ management UI

6. Остановка:

```bash
docker compose down
```

### Выкат новой версии

При смене только кода или миграций на диске образы не обязательно пересобирать. Если правили `Dockerfile` или `requirements.txt` у `app`, `ml-worker` или `web-proxy`, сначала выполните `docker compose build app ml-worker web-proxy`.

```bash
docker compose run --rm app python -m alembic upgrade head  # не нужна, если новых миграций нет
docker compose up -d app ml-worker web-proxy
```

## Для разработки

Ниже локальный запуск backend и frontend без Docker.

### Backend

1. Установите зависимости:

```bash
python -m pip install -r app/requirements.txt
```

2. Примените миграции:

```bash
DATABASE_URL=sqlite:///./safetalk_local.db python -m alembic upgrade head
```

3. Запустите backend:

```bash
PYTHONPATH=. DATABASE_URL=sqlite:///./safetalk_local.db python -m uvicorn app.main:app --reload
```

После старта backend доступен по адресам:

- `http://127.0.0.1:8000` - base URL API
- `http://127.0.0.1:8000/docs` - Swagger UI
- `http://127.0.0.1:8000/docs-public` - публичная документация
- `http://127.0.0.1:8000/health` - health-check

### Frontend / личный кабинет

Локальный frontend настроен без дополнительных переменных в команде запуска: dev-прокси по умолчанию ходит в backend на `http://127.0.0.1:8000`.

1. Убедитесь, что backend уже запущен
2. Перейдите в папку `dashboard`
3. Установите зависимости:

```bash
npm install
```

4. Запустите frontend:

```bash
npm run dev
```

После старта frontend доступен по адресам:

- `http://127.0.0.1:5173/` - статическая страница проекта
- `http://127.0.0.1:5173/dashboard/` - личный кабинет / frontend

Если backend нужен не на `127.0.0.1:8000`, адрес dev-прокси можно изменить в `dashboard/vite.config.ts`.

### Демо-данные для локальной разработки

Если нужны локальные демо-аккаунты и стартовые балансы, их можно добавить отдельной командой:

```bash
python scripts/seed_demo_data.py
```

Эта команда нужна только для локальной разработки и не должна использоваться как часть продового запуска.

## Тесты

Сценарии ручного тестирования собраны в `TESTING_SCENARIOS.md`.

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
- для подробной проверки покрытия можно добавить `--cov-report=html`

Пример:

```bash
python -m pytest tests --cov=app --cov-report=term --cov-report=html
```

## Конфигурация

Пример значений лежит в `app/.env.example`.

Основные группы переменных:

- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DB_NAME`  
  Параметры подключения к PostgreSQL. Используются в Docker-сценарии, когда приложение подключается к контейнеру базы данных. Для запуска через PostgreSQL эти переменные обязательны, если не используется `database_url`.

- `database_url`  
  Альтернативный способ задать подключение к базе одной строкой. Удобен для локального запуска, например с SQLite: `sqlite:///./safetalk_local.db`. Для локального backend это самый простой и фактически обязательный вариант, если вы не хотите отдельно поднимать PostgreSQL.

- `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASS`  
  Параметры подключения к RabbitMQ. Нужны для очереди ML-задач и для работы `ml-worker`. Для полного запуска через `docker compose` обязательны.

- `TELEGRAM_BOT_TOKEN`  
  Токен Telegram-бота для отправки сообщений через Telegram Bot API. Опционален, нужен только если вы используете Telegram-интеграцию.

- `TELEGRAM_WEBHOOK_SECRET_TOKEN`  
  Секретный токен для защиты Telegram webhook. Опционален, нужен только если вы используете Telegram webhook.

- `EMAIL_VERIFICATION_TTL_SECONDS`  
  Сколько секунд живет код подтверждения email. Опциональна, есть значение по умолчанию.

- `EMAIL_VERIFICATION_MAX_ATTEMPTS`  
  Сколько попыток дается на ввод кода подтверждения email. Опциональна, есть значение по умолчанию.

Что использовать на практике:

- для `docker compose` обычно достаточно скопировать `app/.env.example` в `app/.env` - нужные обязательные переменные там уже заполнены
- для локального backend без Docker достаточно указать `DATABASE_URL=sqlite:///./safetalk_local.db`
- Telegram-переменные можно не заполнять, если Telegram-интеграция вам не нужна

## Архитектура

Каждый модуль разделен на слои:

- `routes.py` - HTTP-слой (FastAPI, Pydantic, коды ответов)
- `service.py` - бизнес-правила и координация между модулями
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

## Единый формат ошибок

Глобальные обработчики в `app/core/error_handlers.py` возвращают JSON:

```json
{
  "error": "validation_error",
  "message": "Понятное сообщение об ошибке",
  "details": {}
}
```

Типовые соответствия:

- `ValidationError` -> `400`
- `NotFoundError` -> `404`
- `InsufficientBalanceError` -> `409`
- `RequestValidationError` -> `422`

## Основные API-сценарии

Ниже зафиксирован текущий контракт HTTP API в виде справочной таблицы.

### Пользовательские эндпоинты

| Method | Path | Purpose | Auth | Notes |
|---|---|---|---|---|
| `GET` | `/health` | Liveness probe приложения | No | Проверка, что процесс жив |
| `GET` | `/health/db` | Readiness probe БД | No | Проверка соединения с БД |
| `POST` | `/auth/register` | Регистрация пользователя | No | Создает пользователя и кошелек |
| `POST` | `/telegram/webhook` | Webhook Telegram-бота | Telegram Secret Token | Получает update от Telegram и обрабатывает команды внутри сервиса |
| `POST` | `/auth/verify-email` | Подтверждение email | No | Проверяет код тестового подтверждения |
| `POST` | `/auth/login` | Логин пользователя | No | Возвращает `access_token`; вход только после verify-email |
| `GET` | `/users/me` | Профиль текущего пользователя | Bearer | Требуется токен из `/auth/login` |
| `PATCH` | `/users/me` | Обновление профиля текущего пользователя | Bearer | Можно менять имя |
| `GET` | `/balance/me` | Текущий баланс | Bearer | Баланс текущего пользователя |
| `POST` | `/balance/me/topup` | Пополнение собственного баланса | Bearer | Упрощенное пополнение без платежного шлюза |
| `GET` | `/balance/me/ledger` | История транзакций | Bearer | История пополнений и списаний |
| `GET` | `/predict/models` | Список доступных ML-моделей | Bearer | Нужен для выбора модели |
| `POST` | `/predict` | Создать ML-задачу | Bearer | `user_id` берется из токена; списывает токены и пишет историю |
| `GET` | `/predict/{task_id}` | Получить статус и результат ML-задачи | Bearer | Возвращает итог предсказания |
| `GET` | `/history/me` | История ML-запросов текущего пользователя | Bearer | Показывает запросы и результаты |
| `GET` | `/history/{user_id}` | История ML-запросов | Bearer | Доступ к своему `user_id`, также доступно admin |

### Админские эндпоинты

| Method | Path | Purpose | Auth | Notes |
|---|---|---|---|---|
| `GET` | `/admin/users` | Список пользователей | Bearer (admin) | Показывает пользователей, email и баланс |
| `GET` | `/admin/users/{user_id}` | Просмотр профиля пользователя | Bearer (admin) | Расширенный профиль для администратора |
| `PATCH` | `/admin/users/{user_id}` | Изменение профиля пользователя | Bearer (admin) | Можно менять имя и `allow_negative_balance` |
| `POST` | `/admin/users/{user_id}/topup` | Пополнение баланса пользователя | Bearer (admin) | Админское начисление токенов |
| `POST` | `/admin/users/{user_id}/spend` | Списание баланса пользователя | Bearer (admin) | Админское списание токенов |
| `GET` | `/admin/stats` | Общая статистика системы | Bearer (admin) | Пользователи, балансы, ML-задачи |
| `GET` | `/admin/ledger` | Общий журнал операций | Bearer (admin) | Глобальная лента пополнений и списаний |
| `GET` | `/admin/history` | Общая история ML-запросов | Bearer (admin) | История по всем пользователям |
| `GET` | `/admin/ml-tasks/{task_id}` | Просмотр ML-задачи | Bearer (admin) | Детали любой ML-задачи по `task_id` |

Профиль пользователя хранится в `users`, а способы входа (email/telegram) — в `user_identities`.

