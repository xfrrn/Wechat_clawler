from __future__ import annotations

from pydantic import BaseModel


class Settings(BaseModel):
    cookies_path: str = "cfg/cookies.json"
    qr_save_path: str = "wx_login_qrcode.png"
    raw_data_file: str = "appmsgpublish_result.json"
    links_output_file: str = "title_url_map.json"


settings = Settings()
