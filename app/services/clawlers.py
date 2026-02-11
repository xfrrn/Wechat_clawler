import json
import os
import re
from typing import Dict, Tuple

import requests
from bs4 import BeautifulSoup
from loguru import logger

from app.services.storage import SessionStorage

Session = requests.Session()
HOME_REFERER = (
    "https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN&token={token}"
)


class WechatClient:
    def __init__(self, storage: SessionStorage) -> None:
        self.storage = storage

    def get_fakeid_by_name(
        self, wx_cfg: dict, kw: str
    ) -> Tuple[str | None, dict | None]:
        url = "https://mp.weixin.qq.com/cgi-bin/searchbiz"
        params = {
            "action": "search_biz",
            "begin": 0,
            "count": 5,
            "query": kw,
            "token": wx_cfg.get("token"),
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1",
        }
        token = wx_cfg.get("token")
        if not token:
            logger.warning("token 为空，可能导致 invalid args")
        headers = {
            "Cookie": wx_cfg.get("cookies_str"),
            "User-Agent": wx_cfg.get("user_agent"),
            "Referer": HOME_REFERER.format(token=token or ""),
            "Accept": "application/json, text/plain, */*",
        }
        Session.headers.update(headers)
        resp = Session.get(url, params=params)
        logger.info(f"searchbiz status={resp.status_code}")
        logger.debug(f"searchbiz response={resp.text}")
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        with open("searchbiz_result.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        try:
            fakeid = data.get("list", [{}])[0].get("fakeid")
            logger.info(f"获取到 fakeid: {fakeid}")
            return fakeid, data
        except Exception:
            logger.error("未获取到 fakeid")
            return None, data

    def get_article_list(
        self, wx_cfg: dict, fakeid: str, begin: int = 0, count: int = 5
    ) -> dict:
        url = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"
        params = {
            "sub": "list",
            "sub_action": "list_ex",
            "begin": begin,
            "count": count,
            "fakeid": fakeid,
            "token": wx_cfg.get("token"),
            "lang": "zh_CN",
            "f": "json",
            "ajax": 1,
        }
        token = wx_cfg.get("token")
        if not token:
            logger.warning("token 为空，可能导致 invalid args")
        headers = {
            "Cookie": wx_cfg.get("cookies_str"),
            "User-Agent": wx_cfg.get("user_agent"),
            "Referer": HOME_REFERER.format(token=token or ""),
            "Accept": "application/json, text/plain, */*",
        }
        Session.headers.update(headers)
        resp = Session.get(url, params=params, headers=headers)
        logger.info(f"appmsgpublish status={resp.status_code}")
        logger.debug(f"appmsgpublish response={resp.text}")
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        self.storage.append_json_result("appmsgpublish_result.json", data)
        return data


class ArticleService:
    def __init__(self, storage: SessionStorage | None = None) -> None:
        self.storage = storage or SessionStorage()

    def extract_title_url(
        self,
        input_file: str = "appmsgpublish_result.json",
        output_file: str = "title_url_map.json",
    ) -> None:
        result = {}
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data_list = [data] if isinstance(data, dict) else data

        for entry in data_list:
            publish_page = entry.get("publish_page")
            if not publish_page:
                continue
            try:
                page_obj = json.loads(publish_page)
            except Exception:
                continue
            for pub in page_obj.get("publish_list", []):
                try:
                    info_obj = json.loads(pub.get("publish_info", "{}"))
                except Exception:
                    continue
                for appmsg in info_obj.get("appmsgex", []):
                    title = appmsg.get("title")
                    link = appmsg.get("link")
                    if title and link:
                        link = link.replace("\\/", "/").replace("\\\\/", "/")
                        result[title] = link
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存 title->URL 到 {output_file}")

    def fetch_article_details(self, url: str, timeout: int) -> Dict:
        headers = {
            "Referer": "https://mp.weixin.qq.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        }
        url = url.strip()
        Session.headers.update(headers)
        logger.info("开始请求公众号文章详情")
        resp = Session.get(url, timeout=timeout)
        if resp.status_code == 200:
            logger.info("请求成功")
        else:
            logger.error("请求失败")
            return {"status": 0}
        resp.encoding = resp.apparent_encoding
        status = re.search("当前环境异常，完成验证后即可继续访问", resp.text)
        if status:
            logger.error("环境异常,程序执行失败")
            return {}
        html = resp.text
        soup = BeautifulSoup(html, "lxml")
        logger.info("开始解析文章内容")
        content = soup.find("div", class_="rich_media_content").get_text(
            "\n", strip=True
        )
        title = soup.find(
            "h1", {"class": "rich_media_title", "id": "activity-name"}
        ).get_text(strip=True)
        author = soup.find("a", {"id": "js_name"}).get_text(strip=True)
        biz = (
            re.search(r'var biz\s*=\s*"(.*?)";', html)
            .group(1)
            .replace('" || "', "")
            .replace('"', "")
        )
        if biz:
            logger.info(f"找到公众号{author} fakeid: {biz}")
        else:
            biz = ""
            logger.warning("查找公众号失败")
        create_time = re.search(r"var createTime = '(.*?)';", html).group(1)
        os.makedirs("HTML", exist_ok=True)
        os.makedirs("TEXT", exist_ok=True)
        os.makedirs("DocJson", exist_ok=True)
        file_name = re.sub(r'[\\/:*?"<>|]', "_", f"{author}-{title}-{create_time}.html")
        html_path = os.path.join("HTML", file_name)
        logger.info(f"保存HTML源码到 {os.path.abspath(html_path)}")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        file_name = re.sub(r'[\\/:*?"<>|]', "_", f"{author}-{title}-{create_time}.txt")
        text_path = os.path.join("TEXT", file_name)
        logger.info(f"保存文章文本到 {os.path.abspath(text_path)}")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(content)
        file_name = f"{author} {title}"
        json_path = os.path.join("DocJson", file_name)
        data = {
            "status": 1,
            "content": content,
            "title": title,
            "author": author,
            "create_time": create_time,
            "biz": biz,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data
