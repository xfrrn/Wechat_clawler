import json
import os
import time
from typing import Any, Dict

from loguru import logger

OUTPUT_JSON = os.path.join("cfg", "cookies.json")


class SessionStorage:
    def __init__(self, path: str = OUTPUT_JSON) -> None:
        self.path = path

    def load_session(self) -> Dict[str, Any] | None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            expiry = data.get("expiry")
            if expiry and time.time() < expiry:
                logger.info("复用本地 cookies")
                return data
            logger.warning("cookies 已过期或无效，需重新登录")
            return None
        except Exception:
            logger.info("未找到本地会话文件，需重新登录")
            return None

    def persist_session(self, data: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def append_json_result(self, filename: str, new_data: Any) -> None:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                history = json.load(f)
            if not isinstance(history, list):
                history = [history]
        except Exception:
            history = []
        history.append(new_data)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)


def load_session(path: str) -> Dict[str, Any] | None:
    return SessionStorage(path).load_session()


def persist_session(data: Dict[str, Any], path: str = OUTPUT_JSON) -> None:
    SessionStorage(path).persist_session(data)


def append_json_result(filename: str, new_data: Any) -> None:
    SessionStorage().append_json_result(filename, new_data)
