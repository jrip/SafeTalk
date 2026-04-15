"""Публичная OpenAPI-схема: только пользовательские ручки, без админ/системных внутренних путей."""

from __future__ import annotations

import copy
from typing import Any


_BLOCKED_PATHS_EXACT = {
    "/balance/{user_id}",
    "/balance/{user_id}/ledger",
    "/history/{user_id}",
}


def _is_public_path(path: str) -> bool:
    if path in _BLOCKED_PATHS_EXACT:
        return False
    return not (path.startswith("/admin") or path.startswith("/telegram") or path.startswith("/health"))


def _collect_schema_refs(obj: Any, out: set[str]) -> None:
    if isinstance(obj, dict):
        ref = obj.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            out.add(ref.rsplit("/", 1)[-1])
        for value in obj.values():
            _collect_schema_refs(value, out)
    elif isinstance(obj, list):
        for value in obj:
            _collect_schema_refs(value, out)


def _prune_component_schemas(schema: dict[str, Any]) -> None:
    components = schema.get("components")
    if not isinstance(components, dict):
        return
    schemas = components.get("schemas")
    if not isinstance(schemas, dict):
        return

    used: set[str] = set()
    paths = schema.get("paths")
    if isinstance(paths, dict):
        _collect_schema_refs(paths, used)

    # Добираем вложенные ссылки внутри самих схем (A -> B -> C).
    changed = True
    while changed:
        changed = False
        for name in list(used):
            payload = schemas.get(name)
            if payload is None:
                continue
            before = len(used)
            _collect_schema_refs(payload, used)
            if len(used) != before:
                changed = True

    components["schemas"] = {name: value for name, value in schemas.items() if name in used}


def public_openapi_from_full_schema(full_schema: dict[str, Any]) -> dict[str, Any]:
    schema = copy.deepcopy(full_schema)
    paths = schema.get("paths")
    if isinstance(paths, dict):
        schema["paths"] = {k: v for k, v in paths.items() if _is_public_path(str(k))}
    _prune_component_schemas(schema)
    info = schema.setdefault("info", {})
    info["description"] = (
        "Публичная документация API SafeTalk (без админских и внутренних ручек).\n\n"
        "Для защищенных запросов нужен `Bearer` access token:\n"
        "1. Получите токен через `POST /auth/login`.\n"
        "2. В Swagger нажмите **Authorize** (замок) и вставьте значение как `Bearer <token>`.\n"
        "3. Либо передавайте заголовок `Authorization: Bearer <token>` в клиенте/скрипте."
    )
    return schema
