from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AdapterHealth(BaseModel):
    name: str
    ok: bool
    detail: str = ""
    last_success: datetime | None = None
