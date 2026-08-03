# Job Crawler Web

基于 FastAPI + 轻量前端（Vue3 CDN）的海外求职岗位采集网站骨架。

> 仅搭建基础骨架，暂未接入 Excel 模板标准化。

## 功能模块

- [x] 登录页（JWT 认证，默认账号 `admin / admin123`）
- [x] 渠道管理页：新增/编辑/删除招聘网站，配置站点 URL、CSS 选择器、爬取规则
- [x] 采集任务控制面板：新建任务、手动触发爬虫运行、查看运行日志
- [x] 通用 Playwright 爬虫服务：支持 headless/headed/CDP 三种浏览器模式、滚动加载、弹窗关闭、列表+详情页提取、URL 去重

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy 2.0 (async SQLite) |
| 前端 | Vue 3 (CDN) + 原生 CSS |
| 爬虫 | Playwright for Python |
| 认证 | JWT + passlib |

## 项目结构

```
job-crawler-web/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置
│   ├── database.py          # 异步数据库连接
│   ├── models.py            # 数据模型
│   ├── schemas.py           # Pydantic 模型
│   ├── auth.py              # JWT 认证
│   ├── routers/
│   │   ├── auth.py          # 登录/认证
│   │   ├── channels.py      # 渠道 CRUD
│   │   └── tasks.py         # 任务 CRUD + 运行
│   └── services/
│       └── scraper.py       # 通用 Playwright 爬虫
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── api.js           # API 客户端
│       └── app.js           # Vue 应用
├── run.py                   # 一键启动脚本
├── requirements.txt
├── .env.example
└── README.md
```

## 本地启动教程

### 1. 安装依赖

```bash
cd job-crawler-web
pip install -r backend/requirements.txt
playwright install chromium
```

> Windows 用户若使用 Edge，可跳过 `playwright install`，启动时改为 headed/CDP 模式。

### 2. 配置环境变量（可选）

```bash
cp .env.example .env
```

按需修改 `.env` 中的管理员密码与浏览器配置。

### 3. 启动服务

```bash
python run.py
```

打开浏览器访问：

- 网站首页：http://localhost:8000
- API 文档：http://localhost:8000/api/docs
- 默认账号：`admin / admin123`

## 使用流程

1. **创建渠道**：进入「渠道管理」→ 新增渠道，填写站点入口 URL 与 CSS 选择器。
2. **创建任务**：进入「采集任务」→ 新建任务，选择渠道、设置最大页数/岗位数、选择浏览器模式。
3. **运行任务**：点击任务行的 **▶ 运行**，等待爬虫采集完成。
4. **查看日志**：点击「日志」查看实时运行记录。

## 浏览器模式说明

| 模式 | 适用场景 |
|------|----------|
| 无头模式 (headless=true) | 默认，无需打开窗口，适合服务器运行 |
| 可视化窗口 (headless=false) | 本地调试，可直观看到页面 |
| CDP 连接 (use_cdp=true) | 连接本地已打开的 Chrome 调试端口，复用登录态 |

启动本地 Chrome 调试模式示例：

```bash
# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=C:\chrome-debug

# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=~/chrome-debug
```

## 扩展开发

- 新增招聘网站：仅在「渠道管理」页面配置 URL 和选择器，无需修改代码。
- 后续接入 Excel 标准化：可在 `backend/services/` 下新增 `standardizer.py`，在 `tasks/run` 接口中调用。
- 定时调度：任务表已含 `schedule` 字段，后续可接入 APScheduler 实现 Cron 定时采集。

## 注意事项

- 本项目为骨架版本，爬虫在目标网站结构变化时需要调整对应选择器。
- 高频爬取可能触发反爬，请合理设置 `max_pages`、`max_jobs` 与随机延迟。
