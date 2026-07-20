import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import time
import re
from datetime import datetime
from pathlib import Path
from loguru import logger
import pandas as pd
from playwright.async_api import async_playwright
from sqlalchemy.exc import SQLAlchemyError

from app.database.db import SessionLocal
from app.database import models
from app.database.models import ChinaJoyCompany


class ChinaJoyCrawler:
    def __init__(self):
        from app.database.db import engine
        models.Base.metadata.create_all(bind=engine)
        
        self.session = SessionLocal()
        self.base_url = "https://btb.chinajoy.net"
        self.total_pages = 29
        self.total_collected = 0

    def _start_chrome_debug(self):
        import socket
        import subprocess
        
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
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
        ]
        
        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                try:
                    subprocess.Popen([
                        chrome_path,
                        "--remote-debugging-port=9222",
                        "--user-data-dir=C:\\chrome-debug"
                    ], shell=True)
                    time.sleep(3)
                    logger.info("✅ Chrome 已启动，等待连接...")
                    return True
                except Exception as e:
                    logger.error(f"启动失败: {e}")
                    continue
        
        logger.error("❌ 未找到 Chrome")
        return False

    def clean_text(self, text: str) -> str:
        """清理文本，去掉前缀和多余空格"""
        if not text:
            return ''
        prefixes = ['公司网址：', '公司地址：', '公司规模：', '成立时间：', '往年收入：', '公司简介：']
        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):]
        return text.strip()

    async def parse_company_list(self, page):
        """解析列表页，提取公司信息"""
        companies = []
        
        try:
            await page.wait_for_selector('a.color-hover', timeout=10000)
        except:
            logger.warning("未找到公司列表，可能页面结构不同")
            return companies
        
        items = await page.query_selector_all('a.color-hover')
        
        for item in items:
            href = await item.get_attribute('href')
            if not href:
                continue
            
            if not href.startswith('http'):
                detail_url = self.base_url + href
            else:
                detail_url = href
            
            # 获取父级元素
            parent = await item.query_selector('xpath=..')
            if not parent:
                parent = await item.query_selector('xpath=../..')
            
            # 展位号 - 合并所有 .e-code
            code_elems = await parent.query_selector_all('.e-code') if parent else []
            booth_code_parts = []
            for elem in code_elems:
                text = (await elem.inner_text()).strip()
                if text:
                    booth_code_parts.append(text)
            booth_code = ' '.join(booth_code_parts) if booth_code_parts else ''
            
            # 公司名称
            title_elem = await parent.query_selector('.e-title') if parent else None
            company_name = ''
            if title_elem:
                company_name = (await title_elem.inner_text()).strip()
            
            # logo
            logo_elem = await parent.query_selector('img.cover') if parent else None
            logo = ''
            if logo_elem:
                logo = await logo_elem.get_attribute('src') or ''
                if logo and not logo.startswith('http'):
                    logo = self.base_url + logo
            
            companies.append({
                'detail_url': detail_url,
                'booth_code': booth_code,
                'company_name': company_name,
                'logo': logo,
            })
        
        return companies

    async def get_company_detail(self, page, detail_url: str):
        """获取公司详情页数据"""
        try:
            await page.goto(detail_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(2000)
            
            result = {'detail_url': detail_url}
            
            # 展位号
            code_elems = await page.query_selector_all('.e-code')
            booth_code_parts = []
            for elem in code_elems:
                text = (await elem.inner_text()).strip()
                if text:
                    booth_code_parts.append(text)
            result['booth_code'] = ' '.join(booth_code_parts) if booth_code_parts else ''
            
            # 公司名称
            title_elem = await page.query_selector('.e-title')
            result['company_name'] = (await title_elem.inner_text()).strip() if title_elem else ''
            
            # 公司网址
            website_elem = await page.query_selector('li:nth-of-type(1) p:nth-of-type(1)')
            result['website'] = self.clean_text(await website_elem.inner_text()) if website_elem else ''
            
            # 公司地址
            address_elem = await page.query_selector('li:nth-of-type(1) p:nth-of-type(2)')
            result['address'] = self.clean_text(await address_elem.inner_text()) if address_elem else ''
            
            # 公司规模
            scale_elem = await page.query_selector('li:nth-of-type(2) p:nth-of-type(1)')
            result['company_scale'] = self.clean_text(await scale_elem.inner_text()) if scale_elem else ''
            
            # 成立时间
            year_elem = await page.query_selector('li:nth-of-type(2) p:nth-of-type(2)')
            result['founded_year'] = self.clean_text(await year_elem.inner_text()) if year_elem else ''
            
            # 往年收入
            revenue_elem = await page.query_selector('li:nth-of-type(3) p')
            result['previous_revenue'] = self.clean_text(await revenue_elem.inner_text()) if revenue_elem else ''
            
            # 公司简介
            intro_elem = await page.query_selector('.e-intro')
            result['description'] = self.clean_text(await intro_elem.inner_text()) if intro_elem else ''
            
            # logo
            logo_elem = await page.query_selector('img.cover')
            result['logo'] = await logo_elem.get_attribute('src') if logo_elem else ''
            if result['logo'] and not result['logo'].startswith('http'):
                result['logo'] = self.base_url + result['logo']
            
            return result
            
        except Exception as e:
            logger.error(f"获取详情失败: {e}")
            return None

    def save_to_db(self, company_data: dict) -> bool:
        """保存到数据库"""
        if not company_data or not company_data.get('detail_url'):
            return False
        
        try:
            existing = self.session.query(ChinaJoyCompany).filter(
                ChinaJoyCompany.detail_url == company_data.get('detail_url')
            ).first()
            
            if existing:
                for key, value in company_data.items():
                    if hasattr(existing, key) and value:
                        setattr(existing, key, value)
                self.session.commit()
                logger.debug(f"更新: {company_data.get('company_name')}")
            else:
                company = ChinaJoyCompany(**company_data)
                self.session.add(company)
                self.session.commit()
                logger.debug(f"新增: {company_data.get('company_name')}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"保存失败: {e}")
            self.session.rollback()
            return False

    def export_to_excel(self):
        """导出数据到Excel"""
        try:
            companies = self.session.query(ChinaJoyCompany).all()
            
            if not companies:
                logger.warning("没有数据可导出")
                return
            
            data_list = []
            for company in companies:
                data_list.append({
                    '详情链接': company.detail_url,
                    '展位号': company.booth_code,
                    '公司名称': company.company_name,
                    '公司网址': company.website,
                    '公司地址': company.address,
                    '公司规模': company.company_scale,
                    '成立时间': company.founded_year,
                    '往年收入': company.previous_revenue,
                    '公司简介': company.description,
                    '公司logo': company.logo,
                })
            
            df = pd.DataFrame(data_list)
            
            output_dir = Path(__file__).parent.parent.parent / "data" / "chinajoy"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = output_dir / f"chinajoy_companies_{timestamp}.xlsx"
            
            df.to_excel(str(filename), index=False, engine='openpyxl')
            logger.success(f"📊 数据已导出到: {filename}")
            logger.success(f"📊 共导出 {len(data_list)} 条数据")
            
        except Exception as e:
            logger.error(f"导出Excel失败: {e}")

    async def crawl_all_companies(self):
        """爬取所有页面的公司 - 每家公司单独打开，爬完返回首页"""
        logger.info("=" * 50)
        logger.info("开始爬取 ChinaJoy 所有参展商...")
        logger.info("=" * 50)

        if not self._start_chrome_debug():
            logger.error("无法启动 Chrome，请手动启动")
            return

        async with async_playwright() as p:
            try:
                browser = await p.chromium.connect_over_cdp("http://localhost:9222")
                logger.info("✅ 已连接到真实 Chrome")
            except:
                logger.error("无法连接到 Chrome，请确保已开启调试模式")
                return
            
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            
            # 主页面 - 用于列表页
            main_page = await context.new_page()
            
            # 访问首页
            await main_page.goto(self.base_url, wait_until='domcontentloaded', timeout=30000)
            await main_page.wait_for_timeout(3000)
            
            page_num = 1
            has_next_page = True
            total_companies = 0
            
            while has_next_page:
                logger.info(f"正在爬取第 {page_num} 页...")
                
                await main_page.wait_for_timeout(3000)
                
                companies = await self.parse_company_list(main_page)
                
                if not companies:
                    logger.info(f"第 {page_num} 页无数据，结束")
                    break
                
                logger.info(f"  本页 {len(companies)} 家公司")
                
                for idx, company in enumerate(companies, 1):
                    company_name = company.get('company_name', '未知')
                    detail_url = company.get('detail_url', '')
                    
                    logger.info(f"    [{idx}/{len(companies)}] 正在爬取: {company_name}")

                    detail_page = await context.new_page()
                    try:
                        detail_data = await self.get_company_detail(detail_page, detail_url)
                        if detail_data:
                            # 补充列表页数据
                            if not detail_data.get('booth_code'):
                                detail_data['booth_code'] = company.get('booth_code', '')
                            if not detail_data.get('company_name'):
                                detail_data['company_name'] = company.get('company_name', '')
                            if not detail_data.get('logo'):
                                detail_data['logo'] = company.get('logo', '')
                            
                            if self.save_to_db(detail_data):
                                self.total_collected += 1
                                total_companies += 1
                    except Exception as e:
                        logger.error(f"      爬取 {company_name} 失败: {e}")
                    finally:
                        await detail_page.close()
                        logger.info(f"      📄 详情页已关闭")
                    
                    # 等待一下再爬下一个
                    await asyncio.sleep(0.5)
                
                logger.info(f"  第 {page_num} 页完成，累计已采集 {self.total_collected} 条")
                
                next_button = await main_page.query_selector('a.layui-laypage-next')
                
                if next_button:
                    class_name = await next_button.get_attribute('class') or ''
                    if 'layui-disabled' in class_name:
                        logger.info("⏹️ 已到达最后一页")
                        has_next_page = False
                    else:
                        logger.info("📄 点击下一页...")
                        await next_button.click()
                        await main_page.wait_for_timeout(5000)
                        page_num += 1
                else:
                    logger.info("⏹️ 未找到下一页按钮，已到达最后一页")
                    has_next_page = False
                
                await asyncio.sleep(1)
            
            await main_page.close()
            await browser.close()
        
        logger.info("=" * 50)
        logger.info(f"爬取完成！共采集 {self.total_collected} 条数据")
        logger.info("=" * 50)
        
        self.export_to_excel()

    def close(self):
        self.session.close()


def main():
    crawler = ChinaJoyCrawler()
    try:
        asyncio.run(crawler.crawl_all_companies())
    finally:
        crawler.close()


if __name__ == "__main__":
    main()