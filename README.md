# 微信公众号爬虫项目

## 1. 项目简介
本项目用于最轻量化（我不管你怎么报错了哈哈）自动化登录微信公众平台，抓取公众号信息和文章内容，并支持数据持久化存储。适合数据采集、内容分析等场景。仅供学习使用。

## 2. 环境要求
- Python 3.8 及以上
- Windows 操作系统（建议）
- 浏览器驱动（如 geckodriver for Firefox）
- 推荐使用虚拟环境
- 微信你得有微信公众平台账号，可以去[微信公众平台](https://mp.weixin.qq.com/)注册

## 3. 安装与配置步骤
1. 克隆本项目到本地  
   ```
   git clone https://github.com/CutePigdaddy/Wechat_official_clawler
   cd Wechat_official_clawler
   ```
2. 安装依赖  
   ```
   pip install -r requirements.txt
   ```
3. 下载并配置浏览器驱动（如 geckodriver），确保其在系统 PATH 中。

   可以通过命令行安装：  
   ```
   winget install Mozilla.Firefox
   ```
   或手动前往 [Firefox 官网](https://www.mozilla.org/zh-CN/firefox/new/) 下载并安装。
   geckodriver 是 Firefox 的 WebDriver，Selenium 需要它来驱动浏览器。  
   - 推荐命令行安装：  
     ```
     winget install mozilla.geckodriver
     ```
   - 或手动下载：[geckodriver Releases](https://github.com/mozilla/geckodriver/releases)  
     下载后将 `geckodriver.exe` 放到你的项目目录或添加到系统 PATH 环境变量中。

## 4. 主要目录结构说明
```
Wechat_official_clawler/
│
├── db/                # 数据库相关代码与测试
├── cfg/               # 配置文件目录（如 cookies.json）
├── venv/              # 虚拟环境（可选）
├── auth.py            # 登录与会话管理
├── storage.py         # 文件保存与读取
├── clawlers.py        # 公众号与文章爬取主逻辑
├── requirements.txt   # 依赖库列表
└── README.md          # 项目说明文档
```

## 5. 快速开始
1. 激活虚拟环境（可选）  
   ```
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. 运行test.py
   ```
   python test.py
   ```
这边建议test自己写，因为我是随便写的，函数都封装好在其他py里面了
## 6. 功能说明
- 自动化扫码登录微信公众平台
- 获取并持久化 cookies、token、user-agent 等会话信息
- 搜索公众号并获取 fakeid
- 获取公众号历史文章列表及详情
- 通过公众号文章链接获取公众号fakeid以及文章内容（暂未更新图片获取）
- 数据保存为 JSON 文件，便于后续分析

## 7. 配置文件说明
- `cfg/cookies.json`：保存登录后的 cookies、token、user-agent 等信息
- requirements.txt：项目依赖库列表
- 其他配置可根据实际需求自定义

## 9. 贡献指南
欢迎提交 issue 或 pull request 改进本项目。请确保代码风格统一，并附带必要的注释和说明。

## 10. 许可证（License）
本项目采用 MIT License，详见 LICENSE 文件。

## 11. 联系方式或作者信息
- 作者：CutePigdaddy
- 邮箱：2257601068@qq.com
- GitHub: [CutePigdaddy](https://github.com/CutePigdaddy)

---

## 特别鸣谢

本项目部分思路和实现参考了 [rachelos/we-mp-rss](https://github.com/rachelos/we-mp-rss) 项目，特此致谢！

---

如需补充具体内容或修改，请随时告知！