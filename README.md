# RedID

[English](#english) | [Русский](#русский)

## English

### About

RedID is a web application for creating and maintaining character sheets for Cyberpunk RED. The repository currently contains the backend API and its PostgreSQL database configuration.

Current backend capabilities:

- sign-in through Yandex OAuth and application-issued access/refresh JWT pairs;
- JWT refresh;
- viewing and updating the current user's avatar;
- creating, listing, reading, fully updating, and partially updating the authenticated user's character sheets;
- an HTTP health endpoint and automatically generated OpenAPI documentation.

### Technology stack

- Python 3.12+
- FastAPI and Uvicorn
- Pydantic v2 and pydantic-settings
- PostgreSQL 18 in Docker Compose
- SQLAlchemy 2 with asyncpg
- Alembic
- pytest, Ruff, mypy, and pytest-cov
- Docker and Docker Compose

### Project structure

```text
red-id/
├── .github/workflows/backend-ci.yml  # Backend CI
├── app/backend/
│   ├── migrations/                   # Alembic migrations
│   ├── src/                          # Import root and application source
│   │   ├── auth/                     # OAuth and JWT authentication
│   │   ├── characters/               # Character sheet functionality
│   │   ├── users/                    # User functionality
│   │   └── main.py                   # FastAPI entry point (main:app)
│   ├── tests/
│   ├── .env.example
│   ├── alembic.ini
│   ├── compose.yaml
│   ├── Dockerfile
│   ├── poetry.lock
│   └── pyproject.toml
└── README.md
```

The `app/backend/src/` directory is the import root; there is no additional `redid` Python package.

### Requirements

For the recommended Docker-based setup:

- Docker with the Docker Compose plugin.

For running the backend directly on the host:

- Python 3.12 or newer;
- a reachable PostgreSQL server;
- a Yandex OAuth application for a working sign-in flow.

### Environment configuration

Create exactly one local environment file: `app/backend/.env`. It supplies application settings to the backend and PostgreSQL settings to Docker Compose. The file is ignored by Git and must not be committed.

From the repository root:

```bash
cd app/backend
cp .env.example .env
```

Safe template (use your own secrets):

```dotenv
POSTGRES_DB=redid
POSTGRES_USER=redid
POSTGRES_PASSWORD=replace-with-local-postgres-password
DATABASE_URL=postgresql+asyncpg://redid:replace-with-local-postgres-password@localhost:5432/redid

AUTH__JWT_SECRET=replace-with-a-random-secret-at-least-32-characters
AUTH__JWT_ALGORITHM=HS256
AUTH__ACCESS_TOKEN_TTL_MINUTES=15
AUTH__REFRESH_TOKEN_TTL_DAYS=30
AUTH__STATE_SECRET=replace-with-another-random-secret-at-least-32-characters
AUTH__STATE_TTL_MINUTES=10

YANDEX_OAUTH__CLIENT_ID=replace-with-yandex-client-id
YANDEX_OAUTH__CLIENT_SECRET=replace-with-yandex-client-secret
YANDEX_OAUTH__REDIRECT_URI=http://localhost:8000/api/v1/auth/oauth/yandex/callback
YANDEX_OAUTH__AUTHORIZE_URL=https://oauth.yandex.ru/authorize
YANDEX_OAUTH__TOKEN_URL=https://oauth.yandex.ru/token
YANDEX_OAUTH__USER_INFO_URL=https://login.yandex.ru/info
YANDEX_OAUTH__HTTP_TIMEOUT_SECONDS=10
```

Variables:

| Variable | Purpose | Replace? |
| --- | --- | --- |
| `POSTGRES_DB` | Database created by the Compose PostgreSQL service. | Optional; `redid` is the default. |
| `POSTGRES_USER` | PostgreSQL user created by Compose. | Optional for local development. |
| `POSTGRES_PASSWORD` | Password for the Compose PostgreSQL user. | **Yes.** |
| `DATABASE_URL` | SQLAlchemy async PostgreSQL URL used when the backend runs on the host. | Update it to match the local database credentials. |
| `AUTH__JWT_SECRET` | Secret used to sign application access and refresh JWTs; at least 32 characters. | **Yes.** |
| `AUTH__JWT_ALGORITHM` | Allowed JWT signing algorithm: `HS256`, `HS384`, or `HS512`. | Usually no. |
| `AUTH__ACCESS_TOKEN_TTL_MINUTES` | Access-token lifetime in minutes; must be positive. | Optional. |
| `AUTH__REFRESH_TOKEN_TTL_DAYS` | Refresh-token lifetime in days; must be positive. | Optional. |
| `AUTH__STATE_SECRET` | Separate secret used to sign OAuth state; at least 32 characters. | **Yes.** |
| `AUTH__STATE_TTL_MINUTES` | OAuth state lifetime in minutes; must be positive. | Optional. |
| `YANDEX_OAUTH__CLIENT_ID` | Client ID of the Yandex OAuth application. | **Yes.** |
| `YANDEX_OAUTH__CLIENT_SECRET` | Client secret of the Yandex OAuth application. | **Yes.** |
| `YANDEX_OAUTH__REDIRECT_URI` | Callback URL registered with Yandex. | Verify it matches the registered callback exactly. |
| `YANDEX_OAUTH__AUTHORIZE_URL` | Yandex authorization endpoint. | Normally no. |
| `YANDEX_OAUTH__TOKEN_URL` | Yandex token endpoint. | Normally no. |
| `YANDEX_OAUTH__USER_INFO_URL` | Yandex user-info endpoint. | Normally no. |
| `YANDEX_OAUTH__HTTP_TIMEOUT_SECONDS` | Timeout for requests to Yandex, in seconds; must be positive. | Optional. |

When the backend runs directly on the host, `DATABASE_URL` normally uses `localhost`. Docker Compose overrides this variable for the backend container and uses `postgres`, matching the PostgreSQL service name. Inside the Compose network, `localhost` would refer to the backend container itself and must not be used as the database hostname.

#### Yandex OAuth

Create an OAuth application in the [Yandex OAuth application portal](https://oauth.yandex.ru/). Register this callback URL:

```text
http://localhost:8000/api/v1/auth/oauth/yandex/callback
```

Set the issued credentials in `YANDEX_OAUTH__CLIENT_ID` and `YANDEX_OAUTH__CLIENT_SECRET`, and keep `YANDEX_OAUTH__REDIRECT_URI` identical to the registered callback. Never commit the client secret.

### Run with Docker Compose

All Compose commands below are run from `app/backend/`:

```bash
cd app/backend
cp .env.example .env
# Edit .env and replace all required placeholder values.

docker compose build backend
docker compose up -d
docker compose ps
```

The backend waits for the PostgreSQL healthcheck, applies `alembic upgrade head`, and starts Uvicorn only after the migrations complete successfully. If a migration fails, the application server is not started.

View backend logs:

```bash
docker compose logs -f backend
```

Stop and remove the containers and network:

```bash
docker compose down
```

The named PostgreSQL volume remains intact after a normal `docker compose down`, so local database data is preserved.

> **Warning:** The following command also deletes the PostgreSQL volume and permanently removes the local database data:
>
> ```bash
> docker compose down --volumes
> ```

Neither Compose service has a restart policy, so the services are not configured to start automatically after the Docker daemon starts.

### Run the backend without Docker

Use an existing PostgreSQL server and make sure `DATABASE_URL` in `app/backend/.env` points to it (usually via `localhost`). From the repository root:

```bash
cd app/backend
python3.12 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
cp .env.example .env
# Edit .env and replace all required placeholder values.

python -m alembic upgrade head
uvicorn main:app --app-dir src --host 0.0.0.0 --port 8000
```

If `app/backend/.env` already exists, do not overwrite it; review and update it instead.

### API addresses

- API: `http://localhost:8000`
- Health check: `http://localhost:8000/api/v1/health`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Development checks

Activate the development virtual environment and run these commands from `app/backend/`:

```bash
ruff format --check .
ruff check .
mypy
pytest
pytest --junitxml=test-results.xml --cov=src --cov-report=term-missing --cov-report=xml:coverage.xml
```

To format the code instead of checking formatting:

```bash
ruff format .
```

## Русский

### О проекте

RedID — веб-приложение для создания и ведения листов персонажей Cyberpunk RED. Сейчас репозиторий содержит backend API и конфигурацию его базы данных PostgreSQL.

Текущие возможности backend:

- вход через Yandex OAuth и выпуск собственных пар access/refresh JWT;
- обновление JWT;
- просмотр и изменение аватара текущего пользователя;
- создание, получение списка, просмотр, полное и частичное обновление листов персонажей аутентифицированного пользователя;
- HTTP health endpoint и автоматически сформированная документация OpenAPI.

### Технологический стек

- Python 3.12+
- FastAPI и Uvicorn
- Pydantic v2 и pydantic-settings
- PostgreSQL 18 в Docker Compose
- SQLAlchemy 2 с asyncpg
- Alembic
- pytest, Ruff, mypy и pytest-cov
- Docker и Docker Compose

### Структура проекта

```text
red-id/
├── .github/workflows/backend-ci.yml  # CI для backend
├── app/backend/
│   ├── migrations/                   # Миграции Alembic
│   ├── src/                          # Корень импортов и исходный код
│   │   ├── auth/                     # Аутентификация OAuth и JWT
│   │   ├── characters/               # Работа с листами персонажей
│   │   ├── users/                    # Работа с пользователями
│   │   └── main.py                   # Точка входа FastAPI (main:app)
│   ├── tests/
│   ├── .env.example
│   ├── alembic.ini
│   ├── compose.yaml
│   ├── Dockerfile
│   ├── poetry.lock
│   └── pyproject.toml
└── README.md
```

Каталог `app/backend/src/` является корнем импортируемых модулей; дополнительного Python-пакета `redid` нет.

### Системные требования

Для рекомендуемого запуска через Docker:

- Docker с плагином Docker Compose.

Для запуска backend непосредственно на хосте:

- Python 3.12 или новее;
- доступный сервер PostgreSQL;
- приложение Yandex OAuth для работающего сценария входа.

### Настройка окружения

Необходимо создать ровно один локальный файл окружения: `app/backend/.env`. Он передаёт настройки приложения в backend и настройки PostgreSQL в Docker Compose. Файл игнорируется Git и не должен попадать в коммиты.

Из корня репозитория:

```bash
cd app/backend
cp .env.example .env
```

Безопасный шаблон (используйте собственные секреты):

```dotenv
POSTGRES_DB=redid
POSTGRES_USER=redid
POSTGRES_PASSWORD=replace-with-local-postgres-password
DATABASE_URL=postgresql+asyncpg://redid:replace-with-local-postgres-password@localhost:5432/redid

AUTH__JWT_SECRET=replace-with-a-random-secret-at-least-32-characters
AUTH__JWT_ALGORITHM=HS256
AUTH__ACCESS_TOKEN_TTL_MINUTES=15
AUTH__REFRESH_TOKEN_TTL_DAYS=30
AUTH__STATE_SECRET=replace-with-another-random-secret-at-least-32-characters
AUTH__STATE_TTL_MINUTES=10

YANDEX_OAUTH__CLIENT_ID=replace-with-yandex-client-id
YANDEX_OAUTH__CLIENT_SECRET=replace-with-yandex-client-secret
YANDEX_OAUTH__REDIRECT_URI=http://localhost:8000/api/v1/auth/oauth/yandex/callback
YANDEX_OAUTH__AUTHORIZE_URL=https://oauth.yandex.ru/authorize
YANDEX_OAUTH__TOKEN_URL=https://oauth.yandex.ru/token
YANDEX_OAUTH__USER_INFO_URL=https://login.yandex.ru/info
YANDEX_OAUTH__HTTP_TIMEOUT_SECONDS=10
```

Переменные:

| Переменная | Назначение | Нужно заменить? |
| --- | --- | --- |
| `POSTGRES_DB` | База данных, создаваемая сервисом PostgreSQL в Compose. | Необязательно; значение по умолчанию — `redid`. |
| `POSTGRES_USER` | Пользователь PostgreSQL, создаваемый Compose. | Необязательно для локальной разработки. |
| `POSTGRES_PASSWORD` | Пароль пользователя PostgreSQL в Compose. | **Да.** |
| `DATABASE_URL` | Асинхронный PostgreSQL URL для SQLAlchemy при запуске backend на хосте. | Приведите в соответствие с локальными реквизитами базы. |
| `AUTH__JWT_SECRET` | Секрет подписи access и refresh JWT приложения; не менее 32 символов. | **Да.** |
| `AUTH__JWT_ALGORITHM` | Разрешённый алгоритм подписи JWT: `HS256`, `HS384` или `HS512`. | Обычно нет. |
| `AUTH__ACCESS_TOKEN_TTL_MINUTES` | Срок действия access-токена в минутах; положительное число. | Необязательно. |
| `AUTH__REFRESH_TOKEN_TTL_DAYS` | Срок действия refresh-токена в днях; положительное число. | Необязательно. |
| `AUTH__STATE_SECRET` | Отдельный секрет подписи OAuth state; не менее 32 символов. | **Да.** |
| `AUTH__STATE_TTL_MINUTES` | Срок действия OAuth state в минутах; положительное число. | Необязательно. |
| `YANDEX_OAUTH__CLIENT_ID` | Client ID приложения Yandex OAuth. | **Да.** |
| `YANDEX_OAUTH__CLIENT_SECRET` | Client secret приложения Yandex OAuth. | **Да.** |
| `YANDEX_OAUTH__REDIRECT_URI` | Callback URL, зарегистрированный в Yandex. | Проверьте точное совпадение с зарегистрированным callback. |
| `YANDEX_OAUTH__AUTHORIZE_URL` | Endpoint авторизации Yandex. | Обычно нет. |
| `YANDEX_OAUTH__TOKEN_URL` | Endpoint получения токена Yandex. | Обычно нет. |
| `YANDEX_OAUTH__USER_INFO_URL` | Endpoint получения данных пользователя Yandex. | Обычно нет. |
| `YANDEX_OAUTH__HTTP_TIMEOUT_SECONDS` | Таймаут запросов к Yandex в секундах; положительное число. | Необязательно. |

При запуске backend непосредственно на хосте `DATABASE_URL` обычно содержит `localhost`. Docker Compose переопределяет эту переменную для backend-контейнера и использует `postgres`, совпадающий с именем сервиса PostgreSQL. Внутри сети Compose `localhost` указывал бы на сам backend-контейнер, поэтому использовать его как hostname базы нельзя.

#### Yandex OAuth

Создайте OAuth-приложение в [кабинете приложений Yandex OAuth](https://oauth.yandex.ru/). Зарегистрируйте callback URL:

```text
http://localhost:8000/api/v1/auth/oauth/yandex/callback
```

Укажите выданные реквизиты в `YANDEX_OAUTH__CLIENT_ID` и `YANDEX_OAUTH__CLIENT_SECRET`, а значение `YANDEX_OAUTH__REDIRECT_URI` оставьте идентичным зарегистрированному callback. Никогда не добавляйте client secret в коммиты.

### Запуск через Docker Compose

Все команды Compose ниже выполняются из `app/backend/`:

```bash
cd app/backend
cp .env.example .env
# Отредактируйте .env и замените все обязательные значения-заглушки.

docker compose build backend
docker compose up -d
docker compose ps
```

Backend ожидает успешного healthcheck PostgreSQL, выполняет `alembic upgrade head` и запускает Uvicorn только после успешного завершения миграций. Если миграция завершается с ошибкой, сервер приложения не запускается.

Посмотреть логи backend:

```bash
docker compose logs -f backend
```

Остановить и удалить контейнеры и сеть:

```bash
docker compose down
```

Именованный volume PostgreSQL сохраняется после обычного `docker compose down`, поэтому локальные данные базы не удаляются.

> **Внимание:** следующая команда также удаляет volume PostgreSQL и безвозвратно уничтожает локальные данные базы:
>
> ```bash
> docker compose down --volumes
> ```

Ни у одного сервиса Compose нет политики перезапуска, поэтому сервисы не настроены на автоматический запуск после старта Docker daemon.

### Запуск backend без Docker

Используйте существующий сервер PostgreSQL и убедитесь, что `DATABASE_URL` в `app/backend/.env` указывает на него (обычно через `localhost`). Из корня репозитория:

```bash
cd app/backend
python3.12 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
cp .env.example .env
# Отредактируйте .env и замените все обязательные значения-заглушки.

python -m alembic upgrade head
uvicorn main:app --app-dir src --host 0.0.0.0 --port 8000
```

Если `app/backend/.env` уже существует, не перезаписывайте его — проверьте и обновите существующий файл.

### Адреса API

- API: `http://localhost:8000`
- Healthcheck: `http://localhost:8000/api/v1/health`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Команды разработки и проверок

Активируйте виртуальное окружение и выполняйте команды из `app/backend/`:

```bash
ruff format --check .
ruff check .
mypy
pytest
pytest --junitxml=test-results.xml --cov=src --cov-report=term-missing --cov-report=xml:coverage.xml
```

Чтобы отформатировать код, а не только проверить форматирование:

```bash
ruff format .
```
