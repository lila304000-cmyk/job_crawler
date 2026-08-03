# Job Crawler Web

基于 FastAPI + 轻量前端（Vue3 CDN）的海外求职岗位采集与标准化网站。

> 已接入 3 套 Excel 导入模板，实现采集后自动清洗、标准化、入库，支持岗位列表查看与一键导出合规 Excel。

## 功能模块

- [x] 登录页（JWT 认证，默认账号 `admin / admin123`）
- [x] 渠道管理页：新增/编辑/删除招聘网站，配置站点 URL、CSS 选择器、爬取规则
- [x] 采集任务控制面板：新建任务、手动触发爬虫运行、查看运行日志
- [x] 通用 Playwright 爬虫服务：支持 headless/headed/CDP 三种浏览器模式、滚动加载、弹窗关闭、列表+详情页提取、URL 去重
- [x] **数据标准化**：自动读取企业、岗位、技能 3 套导入模板，按岗位链接去重、统一日期薪资格式、技能匹配标准库
- [x] **岗位列表页**：多条件筛选、搜索、分页、详情弹窗（含标准化数据与匹配技能）
- [x] **Excel 导出**：一键生成完全匹配导入模板的 Excel（平台公司 Sheet + 任务 Sheet）
- [x] **日志模块**：采集、清洗、标准化、导出日志统一存入 CrawlLog

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy 2.0 (async SQLite) |
| 前端 | Vue 3 (CDN) + 原生 CSS |
| 爬虫 | Playwright for Python |
| 认证 | JWT + passlib |
| Excel | openpyxl |

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
│   │   ├── tasks.py         # 任务 CRUD + 运行
│   │   └── jobs.py          # 岗位列表 / 标准化 / Excel 导出
│   └── services/
│       ├── scraper.py       # 通用 Playwright 爬虫
│       ├── standardizer.py  # 数据清洗与模板标准化
│       └── exporter.py      # Excel 导出服务
├── data/
│   └── templates/           # 3 套导入模板
│       ├── platform-company-import-template.xlsx
│       ├── skills_data.xlsx
│       └── task-import-template.xlsx
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
3. **运行任务**：点击任务行的 **▶ 运行**，爬虫会自动采集岗位并触发标准化。
4. **查看岗位**：进入「岗位列表」，可搜索、筛选、查看详情与标准化结果。
5. **导出 Excel**：进入「Excel 导出」，选择任务（可选）后一键下载匹配模板的 Excel。
6. **查看日志**：任务面板中点击「日志」查看采集、清洗、标准化、导出记录。

## 标准化规则说明

系统启动时会自动读取 `data/templates/` 下的 3 份模板：

| 模板 | 用途 |
|------|------|
| `platform-company-import-template.xlsx` | 平台公司导入字段与字段字典 |
| `skills_data.xlsx` | 标准技能库（一/二/三级标签） |
| `task-import-template.xlsx` | 任务导入字段 |

标准化流程：

1. **去重**：以岗位链接 SHA256 哈希为唯一键，采集与入库时自动去重。
2. **清洗**：去除 HTML 标签、HTML 实体、多余空白、常见广告/弹窗文案。
3. **薪资解析**：支持 `$50K-$80K/year`、`10K-20K`、`3万-5万`、`年薪`、`月薪`、`面议` 等多种格式，统一为 `budget_mode/pricing_type/budget_min/budget_max/currency`。
4. **地点解析**：识别国家代码（CN/SG/US 等）与城市，判断 `online_remote` / `offline_office`。
5. **技能匹配**：将标题与描述中的关键词匹配到标准技能库，自动归类。
6. **日期统一**：相对日期（x 天前）与绝对日期统一为 `YYYY-MM-DD`。
7. **模板对齐**：输出字段严格匹配导入模板表头，缺失字段填空。

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
- 定时调度：任务表已含 `schedule` 字段，后续可接入 APScheduler 实现 Cron 定时采集。
- 数据看板：可在 `routers/jobs.py` 的 `/stats` 接口基础上扩展图表。

## 注意事项

- 本项目目标网站结构变化时，需要调整对应渠道的选择器。
- 高频爬取可能触发反爬，请合理设置 `max_pages`、`max_jobs` 与随机延迟。
- CDP 模式需要本地 Chrome 已启动调试端口。
