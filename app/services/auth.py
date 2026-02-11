import datetime
import os
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.services.storage import SessionStorage

WX_LOGIN = "https://mp.weixin.qq.com/"
WX_HOME = "https://mp.weixin.qq.com/cgi-bin/home"
QR_SAVE_PATH = "wx_login_qrcode.png"
OUTPUT_JSON = os.path.join("cfg", "cookies.json")


def wait_first_image_loaded(driver, timeout=20):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script(
            "const img=document.querySelector('img');return img && img.complete;"
        )
    )


def find_qr_element(driver, timeout=20):
    selectors = [
        ".login__type__container__scan__qrcode",
    ]
    for css in selectors:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, css))
            )
            return el
        except Exception:
            continue
    raise RuntimeError("二维码元素未找到，请检查页面结构或更新选择器")


def save_qr_image(driver, el, save_path=QR_SAVE_PATH):
    try:
        el.screenshot(save_path)
        if os.path.getsize(save_path) > 512:
            return
    except Exception:
        pass
    tmp_full = "_full.png"
    driver.save_screenshot(tmp_full)
    loc = el.location
    size = el.size
    from PIL import Image

    with Image.open(tmp_full) as img:
        left, top = int(loc["x"]), int(loc["y"])
        right, bottom = int(loc["x"] + size["width"]), int(loc["y"] + size["height"])
        cropped = img.crop((left, top, right, bottom))
        cropped.save(save_path)
    os.remove(tmp_full)


def extract_token(driver) -> Optional[str]:
    import re

    url = driver.current_url
    m = re.search(r"[?&]token=([^&#]+)", url)
    if m:
        return m.group(1)

    html = driver.page_source or ""
    m = re.search(r"[?&]token=(\d+)", html)
    if m:
        return m.group(1)

    m = re.search(r"\btoken\b\s*[:=]\s*['\"](\d+)['\"]", html)
    if m:
        return m.group(1)

    return None


def extract_token_from_html(html: str) -> Optional[str]:
    import re

    if not html:
        return None
    m = re.search(r"[?&]token=(\d+)", html)
    if m:
        return m.group(1)
    m = re.search(r"\btoken\b\s*[:=]\s*['\"](\d+)['\"]", html)
    if m:
        return m.group(1)
    return None


def fetch_token_from_home(driver) -> Optional[str]:
    try:
        driver.get(WX_HOME)
    except Exception:
        return None
    return extract_token_from_html(driver.page_source or "")


def cookies_and_expiry(driver) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    cookies = driver.get_cookies()
    expiry_ts = None
    exp_list = []
    for c in cookies:
        if "expiry" in c:
            try:
                exp_list.append(int(c["expiry"]))
            except Exception:
                pass
    if exp_list:
        expiry_ts = min(exp_list)
    return cookies, expiry_ts


def format_cookies_str(cookies: List[Dict[str, Any]]) -> str:
    return "; ".join([f"{c['name']}={c['value']}" for c in cookies])


def verify_logged_in(driver, timeout=20) -> bool:
    try:
        WebDriverWait(driver, timeout).until(EC.url_contains("/cgi-bin/home"))
        return True
    except Exception:
        return False


class WechatAuth:
    def __init__(
        self, storage: SessionStorage, qr_save_path: str = QR_SAVE_PATH
    ) -> None:
        self.storage = storage
        self.qr_save_path = qr_save_path

    def login_with_qr(self) -> Dict[str, Any]:
        options = webdriver.FirefoxOptions()
        service = Service()
        driver = webdriver.Firefox(service=service, options=options)
        driver.set_window_size(1280, 900)
        try:
            logger.info("开始获取二维码...")
            driver.get(WX_LOGIN)
            wait_first_image_loaded(driver, timeout=20)
            qr = find_qr_element(driver, timeout=20)
            save_qr_image(driver, qr, self.qr_save_path)
            if os.path.getsize(self.qr_save_path) < 400:
                raise RuntimeError(
                    "二维码图片异常（过小），请重新运行或手动刷新页面后再试"
                )

            logger.info(
                f"已保存二维码: {os.path.abspath(self.qr_save_path)}，请扫描登录..."
            )

            WebDriverWait(driver, 180).until(
                lambda d: ("token=" in d.current_url)
                or ("/cgi-bin/home" in d.current_url)
            )

            token = extract_token(driver)
            home_token = fetch_token_from_home(driver)
            token = home_token or token
            cookies, expiry_ts = cookies_and_expiry(driver)
            cookies_str = format_cookies_str(cookies)

            user_agent = driver.execute_script("return navigator.userAgent;")

            ok = verify_logged_in(driver, timeout=10) or bool(token)
            logger.info(f"登录成功: {ok}, token: {token}")
            if not ok or not token:
                logger.error(
                    "登录未完成或未获取到 token，请确认扫码已完成并具有管理员权限"
                )
                return {}

            data = {
                "token": token,
                "cookies": cookies,
                "cookies_str": cookies_str,
                "user_agent": user_agent,
                "expiry": expiry_ts,
                "expiry_human": (
                    datetime.datetime.utcfromtimestamp(expiry_ts).strftime(
                        "%Y-%m-%d %H:%M:%S UTC"
                    )
                    if expiry_ts
                    else None
                ),
                "saved_at": datetime.datetime.utcnow().strftime(
                    "%Y-%m-%d %H:%M:%S UTC"
                ),
            }
            self.storage.persist_session(data)
            logger.info(f"已保存会话到: {os.path.abspath(self.storage.path)}")
            return data
        finally:
            driver.quit()


def get_cookies():
    storage = SessionStorage(OUTPUT_JSON)
    return WechatAuth(storage=storage, qr_save_path=QR_SAVE_PATH).login_with_qr()
