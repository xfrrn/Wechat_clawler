import requests,json,os,re
from bs4 import BeautifulSoup
from storage import persist_session
from typing import Dict
COKKIES_PATH = os.path.join("cfg","cookies.json")
Session = requests.Session()

def get_fakeid_by_name(wx_cfg, kw):
  """
  根据公众号名称关键词获取公众号的 fakeid。
  
  Args:
    wx_cfg (dict): 包含 token、cookies_str、user_agent 等认证信息的配置字典。
    kw (str): 公众号名称关键词。
  
  Returns:
    str or None: 获取到的 fakeid，未获取到则返回 None。
  """
  url = "https://mp.weixin.qq.com/cgi-bin/searchbiz"
  params = {
    "action": "search_biz",
    "begin": 0,
    "count": 5,
    "query": kw,
    "token": wx_cfg.get("token"),
    "lang": "zh_CN",
    "f": "json",
    "ajax": "1"
  }
  headers = {
    "Cookie": wx_cfg.get("cookies_str"),
    "User-Agent": wx_cfg.get("user_agent")
  }
  Session.headers.update(headers)
  resp = Session.get(url, params=params)
  print("状态码:", resp.status_code)
  print("响应内容:", resp.text)
  # 保留 searchbiz 返回内容
  try:
    data = resp.json()
  except Exception:
    data = resp.text
  with open("searchbiz_result.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
  try:
    fakeid = data["list"][0]["fakeid"]
    print(f"[信息] 获取到 fakeid: {fakeid}")
    return fakeid
  except Exception:
    print("[错误] 未获取到 fakeid")
    return None

def get_article_list(wx_cfg, fakeid, count=5):
  """
  获取指定 fakeid 公众号的历史文章列表。
  
  Args:
    wx_cfg (dict): 包含 token、cookies_str、user_agent 等认证信息的配置字典。
    fakeid (str): 公众号的 fakeid。
    count (int, optional): 获取的文章数量，默认为 5。
  
  Returns:
    None: 结果通过 persist_session 持久化保存。
  """
  url = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"
  params = {
    "sub": "list",
    "sub_action": "list_ex",
    "begin": 0,
    "count": count,
    "fakeid": fakeid,
    "token": wx_cfg.get("token"),
    "lang": "zh_CN",
    "f": "json",
    "ajax": 1
  }
  headers = {
    "Cookie": wx_cfg.get("cookies_str"),
    "User-Agent": wx_cfg.get("user_agent")
  }
  Session.headers.update(headers)
  resp = Session.get(url, params=params, headers=headers)
  print("状态码:", resp.status_code)
  print("响应内容:", resp.text)
  # 保留 appmsgpublish 返回内容
  try:
    data = resp.json()
  except Exception:
    data = resp.text
  persist_session(data,"appmsgpublish_result.json")

def extract_title_url(input_file="appmsgpublish_result.json", output_file="title_url_map.json"):
  """
  从 appmsgpublish_result.json 提取文章标题与 URL 的映射，并保存为 JSON 文件。
  
  Args:
    input_file (str): 输入的 appmsgpublish 结果 JSON 文件路径。
    output_file (str): 输出的标题-URL 映射 JSON 文件路径。
  
  Returns:
    None: 结果写入 output_file。
  """
  import json
  import ast

  result = {}
  with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

  if isinstance(data, dict):
    data_list = [data]
  else:
    data_list = data
  
  for entry in data_list:
    # publish_page 是字符串，需要解析
    publish_page = entry.get("publish_page")
    if not publish_page:
      continue
    try:
      page_obj = json.loads(publish_page)
    except Exception:
      continue
    for pub in page_obj.get("publish_list", []):
      # publish_info 也是字符串
      try:
        info_obj = json.loads(pub.get("publish_info", "{}"))
      except Exception:
        continue
      for appmsg in info_obj.get("appmsgex", []):
        title = appmsg.get("title")
        link = appmsg.get("link")
        if title and link:
          # 处理反斜杠
          link = link.replace("\\/", "/").replace("\\\\/", "/")
          result[title] = link
  # 保存结果
  with open(output_file, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
  print(f"[信息] 已保存 title->URL 到 {output_file}")

def fetch_article_details(url,timeout) -> Dict:
  """
  获取公众号文章详情，包括作者、标题、内容等。
  
  Args:
    url (str): 公众号文章的 URL。
    timeout (int): 请求超时时间（秒）。
  
  Returns:
    dict: 包含 status、content、title、author、create_time、biz 等信息。
      - status=1 表示成功，0 表示失败。
  """
  headers = {
    "Referer": "https://mp.weixin.qq.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
  }
  url = url.strip() #去除头尾空格换行
  Session.headers.update(headers)
  print("-----开始请求-----")
  resp = Session.get(url,timeout=timeout)
  if resp.status_code == 200:
    print("√√√√√请求成功！√√√√√")
  else:
     print("×××××请求失败🥹×××××")
     return {"status":0}
  resp.encoding = resp.apparent_encoding
  status = re.search("当前环境异常，完成验证后即可继续访问",resp.text)
  if status:
    print("!!!!!环境异常,程序执行失败!!!!!!")
    return {}
  html = resp.text
  soup = BeautifulSoup(html,"lxml")
  print("-----开始搜索元素-----")
  content = soup.find("div",class_ = "rich_media_content").get_text("\n",strip=True)
  title = soup.find("h1",{"class":"rich_media_title","id":"activity-name"}).get_text(strip=True)
  author = soup.find("a",{"id":"js_name"}).get_text(strip=True)
  biz = re.search(r'var biz\s*=\s*"(.*?)";',html).group(1).replace('" || "','').replace('"','')
  if(biz):
    print(f"找到公众号{author}fakeid:{biz}，保存后可以用于获取文章列表")
  else:
    biz = ""
    print("查找公众号失败")
  create_time = re.search(r"var createTime = '(.*?)';",html).group(1)
  os.makedirs("HTML",exist_ok=True)
  os.makedirs("TEXT",exist_ok=True)
  os.makedirs("DocJson",exist_ok=True)
  file_name = re.sub(r'[\\/:*?"<>|]', "_", f"{author}-{title}-{create_time}.html")
  html_path = os.path.join("HTML",file_name)
  print(f"-----保存HTML源码到{os.path.abspath(html_path)}-----")
  with open(html_path,"w",encoding="utf-8") as f:
    f.write(html)
  file_name = re.sub(r'[\\/:*?"<>|]', "_", f"{author}-{title}-{create_time}.txt")
  text_path = os.path.join("TEXT",file_name)
  print(f"-----保存文章文本到{os.path.abspath(text_path)}-----")
  with open(text_path,"w",encoding="utf-8") as f:
    f.write(content)
  file_name = f"{author} {title}"
  json_path = os.path.join("DocJson",file_name)
  data = {
    "status":1,
    "content":content,
    "title":title,
    "author":author,
    "create_time":create_time,
    "biz":biz
  }
  persist_session(data,json_path)
  return data
