"""Схема OpenAPI без админских путей (`/admin/*`) — для публичной документации."""

from __future__ import annotations

import copy
from typing import Any


def public_openapi_from_full_schema(full_schema: dict[str, Any]) -> dict[str, Any]:
    schema = copy.deepcopy(full_schema)
    paths = schema.get("paths")
    if isinstance(paths, dict):
        schema["paths"] = {k: v for k, v in paths.items() if not str(k).startswith("/admin")}
    info = schema.setdefault("info", {})
    desc = info.get("description") or ""
    marker = "Публичная спецификация (без `/admin"
    if marker not in desc:
        info["description"] = (
            desc
            + "\n\n---\n\n**Публичная спецификация:** скрыты пути `/admin/*`. "
            "Полная схема: [`/openapi.json`](/openapi.json), интерактивно: [`/docs`](/docs)."
        )
    return schema
