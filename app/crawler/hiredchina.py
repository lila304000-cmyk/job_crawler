import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import random
import re
from datetime import datetime
from pathlib import Path
from loguru import logger
import pandas as pd
from patchright.async_api import async_playwright
from sqlalchemy.exc import SQLAlchemyError

from app.database.db import SessionLocal
from app.database.models import HiredChinaJob


class HiredChinaCrawler:
    def __init__(self):
        self.session = SessionLocal()
        self.base_url = "https://www.hiredchina.com"
        self.language = 'en'
        self.job_data_list = []
        
        # 国家配置: (国家ID, 显示名称, location值, 页数)
        self.country_config = {
            'usa': {'id': 'nationalitie182', 'name': '美国', 'location': 'United States', 'pages': 2},
            'malaysia': {'id': 'nationalitie102', 'name': '马来西亚', 'location': 'Malaysia', 'pages': 1},
            'russia': {'id': 'nationalitie141', 'name': '俄罗斯', 'location': 'Russia', 'pages': 1},
            'brazil': {'id': 'nationalitie24', 'name': '巴西', 'location': 'Brazil', 'pages': 1},
            'germany': {'id': 'nationalitie59', 'name': '德国', 'location': 'Germany', 'pages': 1},
            'japan': {'id': 'nationalitie82', 'name': '日本', 'location': 'Japan', 'pages': 1},
            'korea': {'id': 'nationalitie87', 'name': '韩国', 'location': 'South Korea', 'pages': 1},
            'indonesia': {'id': 'nationalitie74', 'name': '印尼', 'location': 'Indonesia', 'pages': 2},
            'vietnam': {'id': 'nationalitie186', 'name': '越南', 'location': 'Vietnam', 'pages': 2},
            'saudi': {'id': 'nationalitie148', 'name': '沙特阿拉伯', 'location': 'Saudi Arabia', 'pages': 1},
            'thailand': {'id': 'nationalitie171', 'name': '泰国', 'location': 'Thailand', 'pages': 2},
            'singapore': {'id': 'nationalitie152', 'name': '新加坡', 'location': 'Singapore', 'pages': 1},
        }

    def save_job(self, job_data: dict) -> bool:
        try:
            job = HiredChinaJob(
                job_url=job_data.get('job_url', ''),
                title=job_data.get('title', ''),
                salary=job_data.get('salary', ''),
                location=job_data.get('location', ''),
                description=job_data.get('description', ''),
                company_url=job_data.get('company_url', ''),
                company_name=job_data.get('company_name', ''),
                posted_time=job_data.get('posted_time', ''),
                created_at=datetime.now()
            )
            self.session.add(job)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"保存失败: {e}")
            self.session.rollback()
            return False

    async def crawl_country(self, country_key: str):
        if country_key not in self.country_config:
            logger.error(f"未知国家: {country_key}")
            return 0
            
        config = self.country_config[country_key]
        nation_id = config['id']
        country_name = config['name']
        location = config['location']
        max_pages = config['pages']
        
        logger.info(f"开始爬取 {country_name} (ID: {nation_id}, {max_pages}页)")
        total = 0
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                logger.info("✅ 浏览器已启动")

                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US',
                )
                page = await context.new_page()

                for page_num in range(1, max_pages + 1):
                    url = f"{self.base_url}/{self.language}/jobs?nationId={nation_id}&page={page_num}"
                    logger.info(f"📄 第 {page_num}/{max_pages} 页")

                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    await page.wait_for_timeout(5000)

                    for _ in range(3):
                        await page.evaluate("window.scrollBy(0, 800)")
                        await page.wait_for_timeout(1500)

                    job_cards = await page.query_selector_all('a.h-full.block')
                    if not job_cards:
                        job_cards = await page.query_selector_all('a[href*="/job/"]')
                    
                    if not job_cards:
                        logger.warning(f"第 {page_num} 页没有职位")
                        continue

                    logger.info(f"找到 {len(job_cards)} 个职位")

                    for idx, card in enumerate(job_cards):
                        try:
                            href = await card.get_attribute('href')
                            if not href:
                                continue
                            full_url = f"{self.base_url}{href}" if href.startswith('/') else href

                            # 获取发布时间
                            posted_time = ''
                            try:
                                all_spans = await card.query_selector_all('span')
                                for span in all_spans:
                                    text = await span.inner_text()
                                    if text and ('天前' in text or 'ago' in text.lower()):
                                        posted_time = text.strip()
                                        break
                            except:
                                pass

                            detail_page = await context.new_page()
                            try:
                                await detail_page.goto(full_url, wait_until='domcontentloaded', timeout=30000)
                                await detail_page.wait_for_timeout(random.randint(3, 8) * 1000)

                                job_info = {
                                    'location': location,
                                    'posted_time': posted_time,
                                    'job_url': full_url
                                }

                                title_elem = await detail_page.query_selector('h3.text-emerald-700') or await detail_page.query_selector('h1')
                                job_info['title'] = await title_elem.inner_text() if title_elem else ''
                                if not job_info['title']:
                                    await detail_page.close()
                                    continue

                                salary_elem = await detail_page.query_selector('.bg-emerald-100 span') or await detail_page.query_selector('div.font-bold')
                                job_info['salary'] = await salary_elem.inner_text() if salary_elem else ''

                                desc_elem = await detail_page.query_selector('div.bg-background') or await detail_page.query_selector('.description, .job-description')
                                job_info['description'] = await desc_elem.inner_text() if desc_elem else ''

                                company_elem = await detail_page.query_selector('a.gap-2.inline-flex') or await detail_page.query_selector('a[href*="/company/"]')
                                if company_elem:
                                    company_href = await company_elem.get_attribute('href')
                                    if company_href:
                                        job_info['company_url'] = f"{self.base_url}{company_href}" if company_href.startswith('/') else company_href

                                name_elem = await detail_page.query_selector('p.font-medium') or await detail_page.query_selector('.company-name')
                                if name_elem:
                                    job_info['company_name'] = await name_elem.inner_text()
                                elif job_info.get('company_url'):
                                    match = re.search(r'/company/([^/]+)', job_info['company_url'])
                                    if match:
                                        job_info['company_name'] = match.group(1).replace('-', ' ').title()

                                logger.info(f"  [{idx+1}] {job_info['title']} | {location}")

                                if self.save_job(job_info):
                                    total += 1
                                    self.job_data_list.append({
                                        'job_url': full_url,
                                        'title': job_info.get('title', ''),
                                        'salary': job_info.get('salary', ''),
                                        'location': location,
                                        'description': job_info.get('description', ''),
                                        'company_url': job_info.get('company_url', ''),
                                        'company_name': job_info.get('company_name', ''),
                                        'posted_time': posted_time
                                    })

                            except Exception as e:
                                logger.error(f"详情页失败: {e}")
                            finally:
                                await detail_page.close()

                            await asyncio.sleep(random.uniform(1, 2))

                        except Exception as e:
                            logger.error(f"处理失败: {e}")
                            continue

                    await asyncio.sleep(random.uniform(2, 4))

                await browser.close()
                logger.info(f"✅ {country_name} 采集完成，共 {total} 条")
                return total

        except Exception as e:
            logger.error(f"爬取失败: {e}")
            return total

    async def crawl_all_countries(self):
        """爬取所有配置的国家"""
        total_all = 0
        results = {}
        
        logger.info(f"\n{'='*60}")
        logger.info(f"开始批量爬取 {len(self.country_config)} 个国家")
        logger.info(f"{'='*60}\n")
        
        for i, (key, config) in enumerate(self.country_config.items(), 1):
            country_name = config['name']
            pages = config['pages']
            
            logger.info(f"\n{'#'*60}")
            logger.info(f"[{i}/{len(self.country_config)}] 正在爬取: {country_name} ({pages}页)")
            logger.info(f"{'#'*60}\n")
            
            try:
                count = await self.crawl_country(key)
                total_all += count
                results[country_name] = count
                logger.info(f"✅ {country_name} 爬取成功，获得 {count} 条")
            except Exception as e:
                logger.error(f"❌ {country_name} 爬取失败: {e}")
                results[country_name] = 0
            
            if i < len(self.country_config):
                delay = random.randint(5, 10)
                logger.info(f"⏳ 等待 {delay} 秒后继续...")
                await asyncio.sleep(delay)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 批量爬取完成！")
        for name, count in results.items():
            logger.info(f"  {name}: {count} 条")
        logger.info(f"总计: {total_all} 条")
        logger.info(f"{'='*60}\n")
        
        # 导出Excel
        self._export_to_excel()
        return results

    def _export_to_excel(self):
        """导出数据到 data/hiredchina/ 目录"""
        try:
            if not self.job_data_list:
                logger.warning("没有数据可导出")
                return

            output_dir = Path(__file__).parent.parent.parent / "data" / "hiredchina"
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = output_dir / f"hiredchina_jobs_{timestamp}.xlsx"

            df = pd.DataFrame(self.job_data_list)
            df.to_excel(str(filename), index=False, engine='openpyxl')
            logger.success(f"📊 数据已导出到: {filename}")
            logger.success(f"📊 共导出 {len(self.job_data_list)} 条数据")

        except Exception as e:
            logger.error(f"导出Excel失败: {e}")

    async def close(self):
        self.session.close()


async def main():
    crawler = HiredChinaCrawler()
    try:
        await crawler.crawl_all_countries()
    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())