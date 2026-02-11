from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException, Query

from app.schemas import ArticlesResult, LoginStatus, SearchResult
from app.services.auth import WechatAuth
from app.services.clawlers import WechatClient
from app.services.storage import SessionStorage
from app.settings import settings

app = FastAPI(title="Wechat Official Crawler")

storage = SessionStorage(settings.cookies_path)
auth = WechatAuth(storage=storage, qr_save_path=settings.qr_save_path)
client = WechatClient(storage=storage)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/login", response_model=LoginStatus)
def login() -> LoginStatus:
    result = auth.login_with_qr()
    if not result.get("token"):
        return LoginStatus(ok=False, token=None, message="login failed")
    return LoginStatus(ok=True, token=result.get("token"), message="ok")


@app.get("/session", response_model=LoginStatus)
def session_status() -> LoginStatus:
    data = storage.load_session()
    if not data:
        return LoginStatus(ok=False, token=None, message="no valid session")
    return LoginStatus(ok=True, token=data.get("token"), message="ok")


@app.get("/search", response_model=SearchResult)
def search_account(keyword: str = Query(..., min_length=1)) -> SearchResult:
    wx_cfg = storage.load_session()
    if not wx_cfg or not wx_cfg.get("token"):
        raise HTTPException(status_code=401, detail="not logged in")
    fakeid, raw = client.get_fakeid_by_name(wx_cfg, keyword)
    if not fakeid:
        return SearchResult(ok=False, fakeid=None, raw=raw)
    return SearchResult(ok=True, fakeid=fakeid, raw=raw)


@app.get("/articles", response_model=ArticlesResult)
def list_articles(
    fakeid: str = Query(..., min_length=1),
    begin: int = Query(0, ge=0),
    count: int = Query(5, ge=1, le=20),
) -> ArticlesResult:
    wx_cfg = storage.load_session()
    if not wx_cfg or not wx_cfg.get("token"):
        raise HTTPException(status_code=401, detail="not logged in")
    data = client.get_article_list(wx_cfg, fakeid, begin=begin, count=count)
    items = _extract_articles(data)
    return ArticlesResult(ok=True, items=items, raw=data)


def _extract_articles(raw: dict | None) -> list[dict]:
    if not isinstance(raw, dict):
        return []
    publish_page_str = raw.get("publish_page")
    if not publish_page_str:
        return []
    try:
        publish_page = json.loads(publish_page_str)
    except Exception:
        return []
    items: list[dict] = []
    for publish in publish_page.get("publish_list", []):
        publish_info_str = publish.get("publish_info")
        if not publish_info_str:
            continue
        try:
            publish_info = json.loads(publish_info_str)
        except Exception:
            continue
        for appmsg in publish_info.get("appmsgex", []):
            items.append(appmsg)
    return items
