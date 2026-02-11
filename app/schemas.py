from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class LoginStatus(BaseModel):
    ok: bool
    token: str | None = None
    message: str | None = None


class SearchResult(BaseModel):
    ok: bool
    fakeid: str | None = None
    raw: dict[str, Any] | None = None


class ArticlesResult(BaseModel):
    ok: bool
    items: list[dict[str, Any]] | None = None
    raw: dict[str, Any] | None = None
