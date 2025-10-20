#任何与cookies相关的操作
import os, json, time, datetime
from typing import Optional, Tuple, Dict, Any, List
from storage import persist_session
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

WX_LOGIN = "https://mp.weixin.qq.com/"
WX_HOME = "https://mp.weixin.qq.com/cgi-bin/home"
QR_SAVE_PATH = "wx_login_qrcode.png"
OUTPUT_JSON = os.path.join("cfg","cookies.json")

def wait_first_image_loaded(driver, timeout=20):
  """
  等待页面第一个图片元素加载完成。

  Args:
    driver: Selenium WebDriver 实例。
    timeout (int): 最大等待时间（秒），默认 20。

  Returns:
    None
  """
  WebDriverWait(driver, timeout).until(
    lambda d: d.execute_script(
      "const img=document.querySelector('img');return img && img.complete;")
  )

def find_qr_element(driver, timeout=20):
  """
  查找二维码图片元素，兼容多种页面结构。

  Args:
    driver: Selenium WebDriver 实例。
    timeout (int): 最大等待时间（秒），默认 20。

  Returns:
    WebElement: 二维码图片的 WebElement。
  """
  # 兼容多个可能选择器，页面可能改版
  selectors = [
    ".login__type__container__scan__qrcode",  # 项目中使用的 class
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
  """
  保存二维码图片到本地。
  优先使用元素截图，失败则截图整个页面并裁剪。

  Args:
    driver: Selenium WebDriver 实例。
    el: 二维码图片 WebElement。
    save_path (str): 保存路径，默认 QR_SAVE_PATH。

  Returns:
    None
  """
  # 首选：元素截图更稳定
  try:
    el.screenshot(save_path)
    if os.path.getsize(save_path) > 512:
      return
  except Exception:
    pass
  # 回退：整个页面截图再裁剪
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
  """
  从当前页面 URL 中提取 token。

  Args:
    driver: Selenium WebDriver 实例。

  Returns:
    Optional[str]: token 字符串或 None。
  """
  # 1) URL
  url = driver.current_url
  import re
  m = re.search(r"[?&]token=([^&#]+)", url)
  if m:
    return m.group(1)
  else:
    return None

def cookies_and_expiry(driver) -> Tuple[List[Dict[str, Any]], Optional[int]]:
  """
  获取当前页面的 cookies，并提取最早的过期时间。

  Args:
    driver: Selenium WebDriver 实例。

  Returns:
    Tuple[List[Dict[str, Any]], Optional[int]]: cookies 列表和最早过期时间戳（或 None）。
  """
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
  """
  将 cookies 列表格式化为 HTTP 请求头字符串。

  Args:
    cookies (List[Dict[str, Any]]): cookies 列表。

  Returns:
    str: "key1=value1; key2=value2" 形式的字符串。
  """
  return "; ".join([f"{c['name']}={c['value']}" for c in cookies])

def verify_logged_in(driver, timeout=20) -> bool:
  """
  检查是否已成功登录（页面跳转到首页）。

  Args:
    driver: Selenium WebDriver 实例。
    timeout (int): 最大等待时间（秒），默认 20。

  Returns:
    bool: 登录成功返回 True，否则 False。
  """
  try:
    WebDriverWait(driver, timeout).until(EC.url_contains("/cgi-bin/home"))
    return True
  except Exception:
    return False

def get_cookies():
  """
  自动化登录微信公众平台，获取 cookies、token、user-agent 并保存到本地 cookies.json。

  Returns:
    dict: 登录信息字典。
  """
  # 如需无头：options = webdriver.FirefoxOptions(); options.add_argument("-headless")
  options = webdriver.FirefoxOptions()
  options.add_argument("-headless")
  service = Service()  # geckodriver 在 PATH 时可省略 executable_path
  driver = webdriver.Firefox(service=service, options=options)
  driver.set_window_size(1280, 900)
  try:
    print("开始获取二维码...")
    driver.get(WX_LOGIN)
    wait_first_image_loaded(driver, timeout=20)
    qr = find_qr_element(driver, timeout=20)
    save_qr_image(driver, qr, QR_SAVE_PATH)
    if os.path.getsize(QR_SAVE_PATH) < 400:
      raise RuntimeError("二维码图片异常（过小），请重新运行或手动刷新页面后再试")

    print(f"[信息] 已保存二维码: {os.path.abspath(QR_SAVE_PATH)}，请扫描登录...")

    # 等待跳转到首页（扫码后）
    WebDriverWait(driver, 180).until(
      lambda d: ("token=" in d.current_url) or ("/cgi-bin/home" in d.current_url)
    )

     # 提取 token + cookies
    token = extract_token(driver)
    cookies, expiry_ts = cookies_and_expiry(driver)
    cookies_str = format_cookies_str(cookies)
  
    # 获取 User-Agent
    user_agent = driver.execute_script("return navigator.userAgent;")
  
    # 持久化
    data = {
      "token": token,
      "cookies": cookies,
      "cookies_str": cookies_str,
      "user_agent": user_agent, 
      "expiry": expiry_ts,
      "expiry_human": (
        datetime.datetime.utcfromtimestamp(expiry_ts).strftime("%Y-%m-%d %H:%M:%S UTC")
        if expiry_ts else None
      ),
      "saved_at": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
    persist_session(data, OUTPUT_JSON)

    # 校验（可选）
    ok = verify_logged_in(driver, timeout=10)
    print(f"[结果] 登录成功: {ok}, token: {token}")
    print(f"[输出] 已保存会话到: {os.path.abspath(OUTPUT_JSON)}")
  finally:
    # 关闭浏览器
    driver.quit()
  return data


"""开始
  │
  ├─> 创建 Selenium Firefox 浏览器（无头模式）
  │
  ├─> 打开微信公众平台登录页（WX_LOGIN）
  │
  ├─> 等待页面二维码图片加载完成
  │
  ├─> 查找二维码图片元素
  │
  ├─> 截图保存二维码图片到本地
  │
  ├─> 提示用户扫码登录
  │
  ├─> 等待页面跳转到首页（用户扫码并确认登录）
  │
  ├─> 提取 token（从 URL/localStorage/sessionStorage/cookies）
  │
  ├─> 获取 cookies 列表及过期时间
  │
  ├─> 格式化 cookies 为字符串
  │
  ├─> 获取 User-Agent
  │
  ├─> 保存所有会话信息到 JSON 文件
  │
  ├─> 校验是否登录成功
  │
  └─> 关闭浏览器，返回会话数据
结束"""