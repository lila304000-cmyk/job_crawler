import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import random
import subprocess
import time
import socket
from datetime import datetime
from pathlib import Path
from loguru import logger
import pandas as pd
from patchright.async_api import async_playwright

from app.config import settings
from app.database.db import SessionLocal
from app.database.models import BossJob  


class BossCrawler:
    def __init__(self):
        self.session = SessionLocal()
        self.jobs = []
        self.job_data_list = []

    def _start_chrome_debug(self):
        """自动启动 Chrome 调试模式"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', 9222))
            sock.close()
            
            if result == 0:
                logger.info("✅ 检测到已有 Chrome 调试模式运行中，直接连接")
                return True
        except:
            pass

        logger.info("正在启动 Chrome 调试模式...")
        try:
            subprocess.Popen([
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "--remote-debugging-port=9222",
                "--user-data-dir=C:\\chrome-debug"
            ], shell=True)
            time.sleep(3)
            logger.info("✅ Chrome 已启动，等待连接...")
            return True
        except Exception as e:
            logger.error(f"启动 Chrome 失败: {e}")
            return False

    async def crawl(self, keyword: str = "", max_pages: int = 50):
        logger.info(f"开始爬取: {keyword if keyword else 'overseas'}")
        self.jobs = []
        self.job_data_list = []

        if not self._start_chrome_debug():
            logger.error("无法启动 Chrome，请手动启动")
            return

        try:
            async with async_playwright() as p:
                for attempt in range(5):
                    try:
                        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
                        logger.info("✅ 已连接到真实 Chrome")
                        break
                    except:
                        logger.info(f"等待 Chrome 启动... ({attempt+1}/5)")
                        await asyncio.sleep(2)
                else:
                    logger.error("无法连接到 Chrome")
                    return

                context = browser.contexts[0]
                page = context.pages[0] if context.pages else await context.new_page()

                url = "https://www.zhipin.com/overseas/"
                logger.info(f"访问列表页: {url}")
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)

                if 'login' in page.url or 'passport' in page.url:
                    logger.warning("⚠️ 需要登录，请在 Chrome 中手动登录后按回车继续...")
                    input("登录完成后按回车继续...")
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    await page.wait_for_timeout(3000)

                # ===== 滚动逻辑 =====
                logger.info("开始滚动加载职位...")
                stop_scrolling = False
                scroll_count = 0
                all_links = set()

                while not stop_scrolling and scroll_count < max_pages:
                    await page.evaluate("window.scrollBy(0, 800)")
                    await page.wait_for_timeout(1500)
                    scroll_count += 1

                    time_elements = await page.query_selector_all('.job-time, .time, .pub-time, [class*="time"]')
                    for elem in time_elements:
                        try:
                            text = await elem.inner_text()
                            if text and ('个月' in text or '月前' in text):
                                logger.info(f"⏹️ 检测到「{text}」，停止滚动")
                                stop_scrolling = True
                                break
                        except:
                            continue

                    if scroll_count % 10 == 0:
                        logger.info(f"  已滚动 {scroll_count} 次")

                # 收集链接
                job_links = await page.query_selector_all('a[href*="/job_detail/"]')
                for link_elem in job_links:
                    href = await link_elem.get_attribute('href')
                    if href:
                        if href.startswith('/'):
                            full_url = f"https://www.zhipin.com{href}"
                        else:
                            full_url = href
                        all_links.add(full_url)

                all_links = list(all_links)
                logger.info(f"总共找到 {len(all_links)} 个职位链接")

                if not all_links:
                    logger.warning("未找到任何职位")
                    return

                # ===== 抓取详情 =====
                for idx, full_url in enumerate(all_links, 1):
                    logger.info(f"({idx}/{len(all_links)}) 访问: {full_url}")

                    detail_page = await context.new_page()

                    try:
                        await detail_page.goto(full_url, wait_until='domcontentloaded', timeout=30000)

                        wait_time = random.randint(5, 10)
                        logger.info(f"等待 {wait_time} 秒...")
                        await detail_page.wait_for_timeout(wait_time * 1000)

                        # ===== 提取数据 =====
                        job_info = {}

                        # 1. 职位名称 - h1
                        title_elem = await detail_page.query_selector('h1')
                        job_info['title'] = await title_elem.inner_text() if title_elem else ''

                        if not job_info.get('title'):
                            logger.warning(f"页面未加载，跳过")
                            await detail_page.close()
                            continue

                        # 2. 薪资范围 - span.salary
                        salary_elem = await detail_page.query_selector('span.salary')
                        job_info['salary'] = await salary_elem.inner_text() if salary_elem else ''

                        # 3. 招聘地 - a.text-desc
                        location_elem = await detail_page.query_selector('a.text-desc')
                        job_info['location'] = await location_elem.inner_text() if location_elem else ''

                        # 4. 经验要求 - span.text-experiece
                        experience_elem = await detail_page.query_selector('span.text-experiece')
                        job_info['experience'] = await experience_elem.inner_text() if experience_elem else ''

                        # 5. 学历要求 - span.text-degree
                        education_elem = await detail_page.query_selector('span.text-degree')
                        job_info['education'] = await education_elem.inner_text() if education_elem else ''

                        # 6. 公司名称 - a[ka='job-detail-company_custompage']
                        company_elem = await detail_page.query_selector('a[ka="job-detail-company_custompage"]')
                        job_info['company'] = await company_elem.inner_text() if company_elem else ''

                        # 7. 驻外详情 - .job-abroad-detail p
                        overseas_parts = []
                        abroad_elems = await detail_page.query_selector_all('.job-abroad-detail p')
                        for elem in abroad_elems:
                            text = await elem.inner_text()
                            if text:
                                overseas_parts.append(text.strip())
                        job_info['oversea_details'] = ' | '.join(overseas_parts)

                        # 8. 职位描述 - div.job-sec-text
                        desc_elem = await detail_page.query_selector('div.job-sec-text')
                        job_info['description'] = await desc_elem.inner_text() if desc_elem else ''

                        # 9. 发布时间
                        posted_time = ''
                        try:
                            time_elem = await detail_page.query_selector('p.gray')
                            if time_elem:
                                posted_time = await time_elem.inner_text()
                                posted_time = posted_time.replace('页面更新时间：', '').replace('页面更新时间:', '').strip()
                        except:
                            pass

                        job_id = full_url.split('/')[-1].replace('.html', '')

                        logger.info(f"  📌 {job_info.get('title')}")
                        logger.info(f"    薪资: {job_info.get('salary')}")
                        logger.info(f"    公司: {job_info.get('company')}")
                        logger.info(f"    地点: {job_info.get('location')}")

                        # ===== 保存到数据库 =====
                        if job_id and job_info.get('title'):
                            existing = self.session.query(BossJob).filter(BossJob.job_id == job_id).first()
                            if existing:
                                logger.info(f"  ⏭️ 已存在，跳过")
                                await detail_page.close()
                                continue

                            job = BossJob(
                                job_id=job_id,
                                url=full_url,
                                title=job_info.get('title', ''),
                                salary=job_info.get('salary', ''),
                                location=job_info.get('location', ''),
                                experience=job_info.get('experience', ''),
                                education=job_info.get('education', ''),
                                oversea_details=job_info.get('oversea_details', ''),
                                description=job_info.get('description', ''),
                                company=job_info.get('company', ''),
                                posted_time=posted_time
                            )
                            self.session.add(job)
                            self.jobs.append(job)
                            self.session.commit()

                            # 保存用于导出Excel
                            self.job_data_list.append({
                                'url': full_url,
                                'title': job_info.get('title', ''),
                                'salary': job_info.get('salary', ''),
                                'location': job_info.get('location', ''),
                                'experience': job_info.get('experience', ''),
                                'education': job_info.get('education', ''),
                                'oversea_details': job_info.get('oversea_details', ''),
                                'description': job_info.get('description', ''),
                                'company': job_info.get('company', ''),
                                'posted_time': posted_time
                            })

                            logger.info(f"  ✅ 已保存 (累计: {len(self.jobs)})")

                    except Exception as e:
                        logger.error(f"详情页处理失败: {e}")
                    finally:
                        await detail_page.close()
                        logger.info(f"  🚪 已关闭详情页")

                logger.info(f"共采集 {len(self.jobs)} 条新职位")

        except Exception as e:
            logger.error(f"连接失败: {e}")

        # 导出Excel
        self._export_to_excel()
        await self.close()

    def _export_to_excel(self):
        """导出数据到 data/boss/ 目录"""
        try:
            if not self.job_data_list:
                logger.warning("没有数据可导出")
                return

            output_dir = Path(__file__).parent.parent.parent / "data" / "boss"
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = output_dir / f"boss_jobs_{timestamp}.xlsx"

            df = pd.DataFrame(self.job_data_list)
            columns = ['url', 'title', 'salary', 'location', 'experience', 
                      'education', 'oversea_details', 'description', 'company', 'posted_time']
            df = df[columns]

            df.to_excel(str(filename), index=False, engine='openpyxl')
            logger.success(f"📊 数据已导出到: {filename}")
            logger.success(f"📊 共导出 {len(self.job_data_list)} 条数据")

        except Exception as e:
            logger.error(f"导出Excel失败: {e}")

    async def close(self):
        self.session.close()


async def main():
    crawler = BossCrawler()
    await crawler.crawl(max_pages=50)
    await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())