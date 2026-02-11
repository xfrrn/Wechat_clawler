import json
import os
import time

from app.services.auth import WechatAuth
from app.services.clawlers import ArticleService, WechatClient
from app.services.storage import OUTPUT_JSON, SessionStorage
from loguru import logger

# --- 配置 ---
TARGET_KEYWORD = "哥飞"  # <--- 在这里修改您想爬取的公众号
ARTICLES_PER_PAGE = 5
RAW_DATA_FILE = "appmsgpublish_result.json"
LINKS_OUTPUT_FILE = "title_url_map.json"

if __name__ == "__main__":
    # 0. 自动清理上次的爬取结果
    if os.path.exists(RAW_DATA_FILE):
        os.remove(RAW_DATA_FILE)
        logger.info(f"已删除旧数据: {RAW_DATA_FILE}")
    if os.path.exists(LINKS_OUTPUT_FILE):
        os.remove(LINKS_OUTPUT_FILE)
        logger.info(f"已删除旧链接: {LINKS_OUTPUT_FILE}")

    # 1. 登录 (已修复 load_session 的 bug)
    storage = SessionStorage(OUTPUT_JSON)
    wx_cfg = storage.load_session()
    if not wx_cfg:
        logger.info("未找到本地会话，正在尝试登录...")
        wx_cfg = WechatAuth(storage=storage).login_with_qr()

    # 检查登录是否真的成功 (token 是否存在)
    if not wx_cfg or not wx_cfg.get("token"):
        logger.error("登录失败，未获取到 Token。")
        logger.error("重要提示：请确保您使用的是'公众号管理员'微信扫码登录！")
        exit()  # 退出

    logger.info(f"登录成功，Token: {wx_cfg.get('token')[:10]}...")

    client = WechatClient(storage=storage)

    # 2. 搜索公众号
    logger.info(f"正在搜索公众号: {TARGET_KEYWORD}")
    fakeid, _ = client.get_fakeid_by_name(wx_cfg, TARGET_KEYWORD)

    if fakeid:
        logger.info(f"获取到 FakeID: {fakeid}，开始循环获取文章列表...")
        begin = 0

        # 3. 循环获取所有文章列表
        while True:
            logger.info(
                f"正在获取第 {begin // ARTICLES_PER_PAGE + 1} 页 (begin={begin})..."
            )

            # 调用修改后的 get_article_list
            data = client.get_article_list(
                wx_cfg, fakeid, begin=begin, count=ARTICLES_PER_PAGE
            )

            # 4. 检查是否爬取完毕
            try:
                if isinstance(data, str):  # 处理 API 返回错误文本
                    logger.error(f"API 返回错误: {data}")
                    break

                # 检查返回的 JSON 数据中是否还有文章
                publish_page_str = data.get("publish_page")
                if not publish_page_str:
                    logger.warning("未在响应中找到 'publish_page'，爬取结束。")
                    break

                publish_list = json.loads(publish_page_str).get("publish_list", [])
                if not publish_list:
                    logger.warning("文章列表 (publish_list) 为空，爬取结束。")
                    break

            except Exception as e:
                logger.error(f"解析响应失败: {e}，爬取中断。")
                logger.error(f"原始数据: {data}")
                break

            # 准备下一次循环
            begin += ARTICLES_PER_PAGE
            time.sleep(3)  # 礼貌性延迟3秒，防止因请求过快被封禁

        logger.info("所有页面数据已获取完毕。")

        # 5. 统一从原始数据文件中提取所有链接
        if os.path.exists(RAW_DATA_FILE):
            logger.info(f"正在从 {RAW_DATA_FILE} 提取所有链接...")
            ArticleService().extract_title_url(
                input_file=RAW_DATA_FILE, output_file=LINKS_OUTPUT_FILE
            )
            logger.info("--- 任务完成 ---")
            logger.info(f"所有文章链接已保存到: {LINKS_OUTPUT_FILE}")
        else:
            logger.warning(f"未生成 {RAW_DATA_FILE}，无法提取链接。")

    else:
        logger.error(f"未能获取到 {TARGET_KEYWORD} 的 FakeID，请检查登录状态或关键词。")

    # 6. 已删除原来下载文章详情的循环
    logger.info("脚本执行完毕。")
