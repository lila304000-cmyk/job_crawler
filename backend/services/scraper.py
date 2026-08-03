import asyncio
import hashlib
import random
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from loguru import logger
from playwright.async_api import async_playwright, Page
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Channel, CrawlLog, JobRecord, Task
from services.standardizer import StandardizerService


class GenericScraper:
    """通用 Playwright 爬虫，参考 reference_spider 的抓取/清洗逻辑封装。

    支持两种浏览器模式：
    1. headless / headed 模式启动新浏览器（默认）
    2. 连接本地 Chrome CDP 调试端口（适合需要登录态的站点）
    """

    def __init__(self, db: AsyncSession, task_id: int, channel_id: int):
        self.db = db
        self.task_id = task_id
        self.channel_id = channel_id
        self.task: Optional[Task] = None
        self.channel: Optional[Channel] = None
        self.selectors: Dict[str, Any] = {}
        self.rules: Dict[str, Any] = {}
        self.seen_urls: set = set()
        self.saved_count = 0
        self.duplicated_count = 0
        self.failed_count = 0

    async def _load_config(self):
        self.task = await self.db.get(Task, self.task_id)
        self.channel = await self.db.get(Channel, self.channel_id)
        if not self.task or not self.channel:
            raise ValueError("任务或渠道不存在")
        self.selectors = self.channel.selectors or {}
        self.rules = self.channel.crawl_rules or {}

    def _rule(self, key: str, default: Any) -> Any:
        return self.rules.get(key, default)

    def _selector(self, key: str, default: str = "") -> str:
        return self.selectors.get(key) or default

    async def _log(self, level: str, message: str):
        logger.info(f"[Task {self.task_id}] {message}")
        self.db.add(CrawlLog(task_id=self.task_id, level=level, message=message))
        await self.db.commit()

    async def _is_duplicate(self, url: str) -> bool:
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        result = await self.db.execute(
            select(JobRecord).where(
                JobRecord.task_id == self.task_id,
                JobRecord.url_hash == url_hash,
            )
        )
        return result.scalar_one_or_none() is not None

    async def _save_job(self, job: Dict[str, Any]) -> bool:
        url = job.get("url", "")
        if not url or not job.get("title"):
            return False
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        if url in self.seen_urls or await self._is_duplicate(url):
            self.duplicated_count += 1
            return False

        record = JobRecord(
            task_id=self.task_id,
            channel_id=self.channel_id,
            url=url,
            url_hash=url_hash,
            title=(job.get("title") or "")[:500],
            company=(job.get("company") or "")[:255],
            location=(job.get("location") or "")[:255],
            salary=(job.get("salary") or "")[:255],
            description=job.get("description") or "",
            raw_data=job,
        )
        self.db.add(record)
        await self.db.commit()
        self.seen_urls.add(url)
        self.saved_count += 1
        return True

    # ==================== 页面操作工具 ====================

    async def _try_close_popups(self, page: Page):
        """尝试关闭常见弹窗/登录框/Cookie横幅。"""
        selectors = []
        custom = self._selector("cookie_banner", "")
        if custom:
            selectors.append(custom)
        selectors += [
            'button[aria-label="关闭"]',
            'button[aria-label="Close"]',
            'button.modal__dismiss',
            'button.artdeco-modal__dismiss',
            'button[data-test-modal-close-btn]',
            '.artdeco-modal__dismiss',
            'button:has-text("×")',
            'button:has-text("Accept")',
            'button:has-text("I accept")',
            'button:has-text("同意")',
            'button:has-text("确定")',
        ]
        for selector in selectors:
            try:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(300)
                    return True
            except Exception:
                continue
        return False

    async def _scroll_page(self, page: Page):
        """按配置滚动页面以触发懒加载。"""
        scroll_times = self._rule("scroll_times", 3)
        scroll_step = self._rule("scroll_step", 800)
        scroll_delay = self._rule("scroll_delay_ms", 1500)
        for i in range(scroll_times):
            await page.evaluate(f"window.scrollBy(0, {scroll_step})")
            await page.wait_for_timeout(scroll_delay)
            if (i + 1) % 5 == 0:
                await self._log("info", f"已滚动 {i + 1}/{scroll_times} 次")

    async def _extract_text(self, page_or_elem, selector: str, default: str = "") -> str:
        """从页面或元素中提取第一个匹配元素的文本。"""
        if not selector:
            return default
        try:
            elem = await page_or_elem.query_selector(selector)
            if elem:
                text = await elem.inner_text()
                return text.strip()
        except Exception:
            pass
        return default

    async def _extract_href(self, page_or_elem, selector: str, base_url: str = "") -> str:
        """提取链接并拼接为绝对 URL。"""
        if not selector:
            return ""
        try:
            elem = await page_or_elem.query_selector(selector)
            if elem:
                href = await elem.get_attribute("href")
                if href:
                    return urljoin(base_url or self.channel.site_url, href)
        except Exception:
            pass
        return ""

    async def _extract_attribute(self, page_or_elem, selector: str, attr: str) -> str:
        if not selector:
            return ""
        try:
            elem = await page_or_elem.query_selector(selector)
            if elem:
                return (await elem.get_attribute(attr)) or ""
        except Exception:
            pass
        return ""

    # ==================== 列表页与详情页 ====================

    async def _parse_list_page(self, page: Page) -> List[Dict[str, Any]]:
        """解析列表页，返回岗位摘要列表（含详情页URL）。"""
        await self._scroll_page(page)
        await self._try_close_popups(page)

        job_card_selector = self._selector("job_card", "")
        list_container_selector = self._selector("list_container", "")

        cards = []
        if job_card_selector:
            cards = await page.query_selector_all(job_card_selector)
        if list_container_selector and not cards:
            container = await page.query_selector(list_container_selector)
            if container:
                cards = await container.query_selector_all(self._selector("job_card", "> div, > li, > article"))
        if not cards:
            # 兜底：尝试常见职位链接
            cards = await page.query_selector_all('a[href*="job"], a[href*="career"], .job-card, [class*="job"]')

        await self._log("info", f"列表页找到 {len(cards)} 个候选卡片")

        jobs = []
        for card in cards:
            try:
                detail_url = await self._extract_href(card, self._selector("detail_link", "a[href]"))
                if not detail_url:
                    continue

                summary = {
                    "url": detail_url,
                    "title": await self._extract_text(card, self._selector("title", "")),
                    "company": await self._extract_text(card, self._selector("company", "")),
                    "location": await self._extract_text(card, self._selector("location", "")),
                    "salary": await self._extract_text(card, self._selector("salary", "")),
                    "description": "",
                }
                jobs.append(summary)
            except Exception as e:
                logger.warning(f"解析列表卡片失败: {e}")
                continue

        return jobs

    async def _parse_detail_page(self, page: Page, summary: Dict[str, Any]) -> Dict[str, Any]:
        """访问详情页并提取完整数据，优先使用详情页选择器覆盖列表页数据。"""
        url = summary["url"]
        detail = dict(summary)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            wait_ms = self._rule("wait_after_detail_ms", 3000)
            await page.wait_for_timeout(wait_ms)
            await self._try_close_popups(page)

            # 详情页字段覆盖
            detail_title = await self._extract_text(page, self._selector("detail_title", "h1"))
            if detail_title:
                detail["title"] = detail_title

            detail_company = await self._extract_text(page, self._selector("detail_company", ""))
            if detail_company:
                detail["company"] = detail_company

            detail_location = await self._extract_text(page, self._selector("detail_location", ""))
            if detail_location:
                detail["location"] = detail_location

            detail_salary = await self._extract_text(page, self._selector("detail_salary", ""))
            if detail_salary:
                detail["salary"] = detail_salary

            detail_desc = await self._extract_text(page, self._selector("detail_description", ""))
            if detail_desc:
                detail["description"] = self._clean_text(detail_desc)
            elif summary.get("description"):
                detail["description"] = self._clean_text(summary["description"])

            # 兜底描述
            if not detail["description"]:
                for selector in ['div.job-sec-text', 'div.description', '.show-more-less-html__markup', '[class*="description"]']:
                    desc = await self._extract_text(page, selector)
                    if len(desc) > 20:
                        detail["description"] = self._clean_text(desc)
                        break

        except Exception as e:
            logger.warning(f"详情页解析失败 {url}: {e}")
            self.failed_count += 1

        return detail

    @staticmethod
    def _clean_text(text: str) -> str:
        """基础文本清洗：去除多余空白、HTML实体、常见广告文案。"""
        if not text:
            return ""
        # 去除 HTML 标签
        text = re.sub(r"<[^>]+>", "", text)
        # 去除多余空白
        text = re.sub(r"\s+", " ", text)
        # 去除常见广告/导航文案
        ad_patterns = [
            r"订阅相似职位.*?(?:$|更多职位)",
            r"更多职位[\s\S]*?(?:$|立即发布)",
            r"在招人？[\s\S]*?(?:$|关于)",
            r"解锁有关.*?招聘洞察",
            r"Chart.*?End of interactive chart\.",
            r"试用 Premium.*?提醒您。",
        ]
        for pattern in ad_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
        return text.strip()

    # ==================== 主流程 ====================

    async def run(self) -> Dict[str, Any]:
        await self._load_config()
        await self._log("info", f"开始采集: {self.channel.name} -> {self.channel.site_url}")

        self.task.status = "running"
        await self.db.commit()

        result = {
            "task_id": self.task_id,
            "status": "success",
            "total": 0,
            "saved": 0,
            "duplicated": 0,
            "failed": 0,
            "message": "",
        }

        try:
            async with async_playwright() as p:
                browser = await self._launch_browser(p)
                context = browser.contexts[0] if browser.contexts else await browser.new_context(
                    user_agent=self._rule("user_agent", None),
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                )
                page = await context.new_page()

                max_pages = min(self.task.max_pages or self._rule("max_pages", 5), 100)
                max_jobs = min(self.task.max_jobs or self._rule("max_jobs", 200), 5000)

                for page_num in range(1, max_pages + 1):
                    if self.saved_count >= max_jobs:
                        await self._log("info", f"达到最大岗位数 {max_jobs}，停止")
                        break

                    list_url = self._build_list_url(self.channel.site_url, page_num)
                    await self._log("info", f"访问列表页 {page_num}/{max_pages}: {list_url}")

                    try:
                        await page.goto(list_url, wait_until="domcontentloaded", timeout=60000)
                        wait_ms = self._rule("wait_after_goto_ms", 3000)
                        await page.wait_for_timeout(wait_ms)
                    except Exception as e:
                        await self._log("error", f"列表页访问失败: {e}")
                        break

                    jobs = await self._parse_list_page(page)
                    await self._log("info", f"第 {page_num} 页解析出 {len(jobs)} 条岗位")

                    if not jobs:
                        await self._log("info", "无更多岗位，结束采集")
                        break

                    for summary in jobs:
                        if self.saved_count >= max_jobs:
                            break

                        detail_page = await context.new_page()
                        try:
                            detail = await self._parse_detail_page(detail_page, summary)
                            if detail.get("title"):
                                await self._save_job(detail)
                        finally:
                            await detail_page.close()

                        delay = random.uniform(
                            self._rule("random_delay_min", 1.0),
                            self._rule("random_delay_max", 3.0),
                        )
                        await asyncio.sleep(delay)

                    # 下一页
                    next_selector = self._selector("next_page", "")
                    if next_selector and page_num < max_pages:
                        has_next = await page.query_selector(next_selector)
                        if not has_next:
                            await self._log("info", "未检测到下一页按钮，结束")
                            break

                await browser.close()

            result.update({
                "total": self.saved_count + self.duplicated_count + self.failed_count,
                "saved": self.saved_count,
                "duplicated": self.duplicated_count,
                "failed": self.failed_count,
                "message": f"采集完成，新增 {self.saved_count} 条",
            })
            await self._log("info", result["message"])

        except Exception as e:
            result["status"] = "failed"
            result["message"] = str(e)
            await self._log("error", f"采集异常: {e}")
            logger.exception("采集异常")

        self.task.status = result["status"]
        self.task.last_run_at = datetime.utcnow()
        self.task.last_run_result = result
        await self.db.commit()
        return result

    async def _launch_browser(self, p):
        use_cdp = self.task.use_cdp if self.task.use_cdp is not None else self._rule("use_cdp", False)
        cdp_url = self.task.cdp_url or self._rule("cdp_url", "http://localhost:9222")
        headless = self.task.headless if self.task.headless is not None else self._rule("headless", True)

        if use_cdp and cdp_url:
            await self._log("info", f"连接 Chrome CDP: {cdp_url}")
            for attempt in range(5):
                try:
                    return await p.chromium.connect_over_cdp(cdp_url)
                except Exception:
                    await asyncio.sleep(2)
            raise ConnectionError(f"无法连接到 CDP: {cdp_url}")

        await self._log("info", f"启动新浏览器 (headless={headless})")
        return await p.chromium.launch(headless=headless)

    def _build_list_url(self, site_url: str, page_num: int) -> str:
        if page_num == 1:
            return site_url
        # 若 URL 中已有 page= 参数则替换
        if "page=" in site_url:
            return re.sub(r"page=\d+", f"page={page_num}", site_url)
        separator = "&" if "?" in site_url else "?"
        return f"{site_url}{separator}page={page_num}"


async def run_scraper(db: AsyncSession, task_id: int, channel_id: int) -> Dict[str, Any]:
    scraper = GenericScraper(db, task_id, channel_id)
    result = await scraper.run()

    # 采集完成后自动触发标准化
    if result.get("status") in ("success", "failed") and result.get("saved", 0) > 0:
        try:
            standardizer = StandardizerService(db)
            std_stats = await standardizer.standardize_task_jobs(task_id)
            result["standardized"] = std_stats
            await scraper._log("info", f"自动标准化完成: 处理{std_stats['processed']}条, 更新{std_stats['updated']}条")
        except Exception as e:
            await scraper._log("error", f"自动标准化失败: {e}")
            result["standardized"] = {"error": str(e)}

    return result
