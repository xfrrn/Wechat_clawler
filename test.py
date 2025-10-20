import requests
import json
import time
from auth import get_cookies
from storage import load_session
from clawlers import*
if __name__ == "__main__":
  wx_cfg = load_session()
  if not wx_cfg:
    wx_cfg = get_cookies()
  kw = "南京大学"
  fakeid = get_fakeid_by_name(wx_cfg, kw)
  if fakeid:
    get_article_list(wx_cfg, fakeid, count=5)
    extract_title_url()  # 新增调用
  with open("title_url_map.json","r",encoding="utf-8") as f:
    maps = json.load(f)
  
  for title,url in maps.items():
    fetch_article_details(url,wx_cfg,timeout=100)