from __future__ import annotations

import os

from fastapi import FastAPI

app = FastAPI(title="SafeTalk")


@app.get("/health")
def health() -> dict[str, str]:
    _ = os.environ.get("DATABASE_URL", "")
    return {"status": "ok"}
