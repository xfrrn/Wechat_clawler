import time,json,os
from typing import Dict, Any
OUTPUT_JSON = os.path.join("cfg","cookies.json")
def load_session(path):
  """
  从 JSON 文件读取会话信息。

  Args:
    path (str): 要读取的 JSON 文件路径。

  Returns:
    dict or None: 读取到的会话信息字典，若无效或过期返回 None。
  """
  try:
    with open(path, "r", encoding="utf-8") as f:
      data = json.load(f)
    expiry = data.get("expiry")
    if expiry and time.time() < expiry:
      print("[信息] 复用本地 cookies")
      return data
    else:
      print("[信息] cookies 已过期或无效，需重新登录")
      return None
  except Exception:
    print("[信息] 未找到本地会话文件，需重新登录")
    return None
  
def persist_session(data: Dict[str, Any], path=OUTPUT_JSON):
  """
  将会话信息保存到 JSON 文件。

  Args:
    data (Dict[str, Any]): 要保存的会话信息字典。
    path (str): 保存的文件路径，默认 OUTPUT_JSON。

  Returns:
    None
  """
  with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    
def append_json_result(filename, new_data):
  """
  向 JSON 文件追加一条新数据，自动处理为列表结构。

  Args:
    filename (str): 目标 JSON 文件路径。
    new_data (Any): 要追加的数据。

  Returns:
    None
  """
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