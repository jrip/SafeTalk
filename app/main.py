from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from app.core.error_handlers import register_exception_handlers
from app.core.public_openapi import public_openapi_from_full_schema
from app.core.settings import validate_settings
from app.modules.billing.routes import router as balance_router
from app.modules.history.routes import router as history_router
from app.modules.neural.routes import router as predict_router
from app.modules.system.routes import router as system_router
from app.modules.telegram.routes import router as telegram_router
from app.modules.admin.routes import router as admin_router
from app.modules.users.routes import router as auth_router, users_router


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )


_configure_logging()
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    validate_settings()
    log.info("Application startup complete. Ensure database migrations are applied before serving traffic.")
    yield


app = FastAPI(
    title="SafeTalk",
    lifespan=lifespan,
    description=(
        "Для защищённых ручек нажми **Authorize** (замок вверху страницы /docs), "
        "вставь только токен из `POST /auth/login` без префикса `Bearer`."
    ),
    swagger_ui_parameters={
        "persistAuthorization": True,
        "tryItOutEnabled": True,
    },
)
register_exception_handlers(app)
app.include_router(system_router)
app.include_router(auth_router)
app.include_router(telegram_router)
app.include_router(users_router)
app.include_router(balance_router)
app.include_router(predict_router)
app.include_router(history_router)
app.include_router(admin_router)


_DOCS_PUBLIC_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>SafeTalk — публичное API</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css" crossorigin="anonymous"/>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js" crossorigin="anonymous"></script>
  <script>
    window.onload = function () {
      SwaggerUIBundle({
        url: "/openapi-public.json",
        dom_id: "#swagger-ui",
        persistAuthorization: true,
      });
    };
  </script>
</body>
</html>"""


@app.get("/openapi-public.json", include_in_schema=False)
def openapi_public_json() -> JSONResponse:
    """OpenAPI без путей `/admin/*` (для клиентов и внешней документации)."""
    return JSONResponse(public_openapi_from_full_schema(app.openapi()))


@app.get("/docs-public", include_in_schema=False)
def docs_public() -> HTMLResponse:
    """Swagger UI по публичной схеме (`/openapi-public.json`)."""
    return HTMLResponse(_DOCS_PUBLIC_HTML)
