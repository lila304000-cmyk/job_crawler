import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import random
import re
import subprocess
import time
import socket
from datetime import datetime
from pathlib import Path
from loguru import logger
import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from sqlalchemy.exc import SQLAlchemyError

from app.database.db import SessionLocal
from app.database.models import HimalayasJob


class HimalayasCrawler:
    def __init__(self):
        self.session = SessionLocal()
        self.base_url = "https://himalayas.app"
        self.job_data_list = []
        self.is_logged_in = False

    def _start_chrome_debug(self):
        """启动Chrome调试模式"""
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

    def save_job(self, job_data: dict) -> bool:
        """保存职位到数据库"""
        try:
            job = HimalayasJob(
                job_url=job_data.get('job_url', ''),
                title=job_data.get('title', ''),
                apply_url=job_data.get('apply_url', ''),
                description=job_data.get('description', ''),
                job_category=job_data.get('job_category', ''),
                job_style=job_data.get('job_style', ''),
                country=job_data.get('country', ''),
                salary=job_data.get('salary', ''),
                company=job_data.get('company', ''),
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

    async def _extract_from_body(self, page):
        """从页面body中提取文本"""
        try:
            return await page.inner_text('body')
        except:
            return ''

    async def _check_login_status(self, page) -> bool:
        """检查是否已登录"""
        try:
            login_btn = await page.query_selector('a:has-text("Sign in")')
            if login_btn and await login_btn.is_visible():
                return False
            
            user_menu = await page.query_selector('[data-testid="user-menu"]')
            if user_menu:
                return True
            
            if 'login' in page.url or 'signin' in page.url:
                return False
            
            return True
        except:
            return True

    async def _wait_for_login(self, page, list_url: str):
        """等待用户重新登录"""
        logger.warning("=" * 50)
        logger.warning("⚠️ 登录已失效，请重新登录！")
        logger.warning("请在浏览器中完成登录操作")
        logger.warning("登录完成后，回到此窗口按回车键继续...")
        logger.warning("=" * 50)
        input("按回车键继续...")
        
        await page.goto(list_url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(5000)
        
        if await self._check_login_status(page):
            logger.info("✅ 重新登录成功！继续爬取...")
            return True
        else:
            logger.warning("⚠️ 仍未检测到登录状态，请确认已登录")
            return False

    async def _get_apply_url(self, page, url: str) -> str:
        """获取申请链接"""
        apply_url = ''
        new_page = None

        try:
            await page.wait_for_load_state('domcontentloaded', timeout=10000)
            await page.wait_for_timeout(1500)

            apply_selectors = [
                'button:has-text("Apply now")',
                'button:has-text("Apply")',
                'button[class*="bg-primary-700"]',
                'button.w-full.flex-grow',
            ]
            
            apply_btn = None
            for selector in apply_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem and await elem.is_visible():
                        apply_btn = elem
                        break
                except:
                    continue

            if not apply_btn:
                return ''

            await apply_btn.click()
            await page.wait_for_timeout(2000)

            ready_selectors = [
                'a:has-text("I\'m ready to apply")',
                'a:has-text("Im ready to apply")',
                'a:has-text("Ready to apply")',
                'a[href*="/apply/"]',
                'a.w-full.sm\\:justify-start',
            ]
            
            ready_link = None
            for selector in ready_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem and await elem.is_visible():
                        ready_link = elem
                        break
                except:
                    continue

            if not ready_link:
                return ''

            try:
                async with page.context.expect_page(timeout=20000) as new_page_info:
                    await ready_link.click()
                
                new_page = await new_page_info.value
                await new_page.wait_for_load_state('domcontentloaded', timeout=15000)
                await new_page.wait_for_timeout(5000)
                
                final_url = new_page.url
                if final_url:
                    apply_url = final_url
                    
            except Exception as e:
                try:
                    href = await ready_link.get_attribute('href')
                    if href:
                        full_url = f"{self.base_url}{href}" if href.startswith('/') else href
                        if full_url:
                            apply_url = full_url
                except:
                    pass

            if new_page:
                try:
                    await new_page.close()
                except:
                    pass

            return apply_url

        except Exception as e:
            if new_page:
                try:
                    await new_page.close()
                except:
                    pass
            return ''

    async def _extract_detail(self, page, url):
        """从详情页提取数据"""
        try:
            job_info = {'job_url': url}

            # 标题
            title = ''
            title_elem = await page.query_selector('h1')
            if title_elem:
                title = await title_elem.inner_text()
                title = title.strip() if title else ''
            if not title:
                title = await page.title()
                title = title.strip() if title else ''
            
            if not title or title == 'himalayas.app':
                return None
            job_info['title'] = title

            body_text = await self._extract_from_body(page)

            # 公司
            company = ''
            company_elem = await page.query_selector('a[href*="/companies/"]')
            if company_elem:
                company = await company_elem.inner_text()
                company = company.strip() if company else ''
            if not company:
                match = re.search(r'/companies/([^/]+)/', url)
                if match:
                    company = match.group(1).replace('-', ' ').title()
            job_info['company'] = company

            # 国家
            country = ''
            try:
                country_match = re.search(r'Location requirements\s*(.+?)(?:Hiring timezones|Job categories|Skills|$)', body_text, re.IGNORECASE | re.DOTALL)
                if country_match:
                    country_text = country_match.group(1).strip()
                    countries = []
                    for line in country_text.split('\n'):
                        line = line.strip()
                        if line and 'Suggest an edit' not in line and len(line) > 2:
                            if '/' in line or '|' in line:
                                parts = re.split(r'[\/|]', line)
                                for p in parts:
                                    p = p.strip()
                                    if p and len(p) > 2:
                                        countries.append(p)
                            else:
                                countries.append(line)
                    country = ' | '.join(countries)
            except:
                pass
            job_info['country'] = country

            # 工作类型
            job_style = ''
            try:
                style_match = re.search(r'Job type\s*(.+?)(?:Experience level|Salary|$)', body_text, re.IGNORECASE | re.DOTALL)
                if style_match:
                    style_text = style_match.group(1).strip()
                    style_text = style_text.strip(': ').strip()
                    if 'Full Time' in style_text:
                        job_style = 'Full-time'
                    elif 'Part Time' in style_text:
                        job_style = 'Part-time'
                    elif 'Contract' in style_text:
                        job_style = 'Contract'
                    else:
                        first_line = style_text.split('\n')[0].strip()
                        if first_line:
                            job_style = first_line
            except:
                pass
            job_info['job_style'] = job_style

            # 薪资
            salary = ''
            salary_patterns = [
                r'([$€£]\s*[\d,.Kk]+)\s*[–—-]\s*([$€£]\s*[\d,.Kk]+)\s*(per\s*(month|year|hour|week|day))?',
                r'([$€£]\s*[\d,.Kk]+)\s*(per\s*(month|year|hour|week|day))',
                r'([$€£]\s*[\d,.Kk]+)',
            ]
            for pattern in salary_patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    try:
                        if len(match.groups()) >= 3 and match.group(3):
                            period = match.group(3).strip().lower()
                            if 'month' in period:
                                salary = f"{match.group(1)} – {match.group(2)}/month" if match.group(2) else f"{match.group(1)}/month"
                            elif 'year' in period:
                                salary = f"{match.group(1)} – {match.group(2)}/year" if match.group(2) else f"{match.group(1)}/year"
                            elif 'hour' in period:
                                salary = f"{match.group(1)} – {match.group(2)}/hour" if match.group(2) else f"{match.group(1)}/hour"
                            else:
                                salary = f"{match.group(1)} – {match.group(2)}" if match.group(2) else match.group(1)
                        elif match.group(1) and match.group(2):
                            salary = f"{match.group(1)} – {match.group(2)}"
                        else:
                            salary = match.group(1)
                        break
                    except:
                        continue
            if not salary:
                salary = 'Negotiable'
            job_info['salary'] = salary

            # 岗位分类
            category = ''
            try:
                category_match = re.search(r'Job categories?\s*(.+?)(?:Skills|Location|About|$)', body_text, re.IGNORECASE | re.DOTALL)
                if category_match:
                    cat_text = category_match.group(1).strip()
                    categories = []
                    for line in cat_text.split('\n'):
                        line = line.strip()
                        if line and len(line) > 2 and not line.startswith('View'):
                            if '/' in line or '|' in line:
                                parts = re.split(r'[\/|]', line)
                                for p in parts:
                                    p = p.strip()
                                    if p and len(p) > 2:
                                        categories.append(p)
                            else:
                                categories.append(line)
                    category = ' | '.join(categories)
            except:
                pass
            
            if not category:
                title = job_info.get('title', '')
                category_keywords = {
                    'Management': ['Manager', 'Director', 'Leader', 'Head'],
                    'Sales': ['Sales', 'Account', 'BD', 'Business Development'],
                    'Technology': ['Engineer', 'Developer', 'Tech', 'Programmer', 'Python', 'Java', 'React', 'Node'],
                    'Marketing': ['Marketing', 'Brand', 'PR'],
                    'Finance': ['Finance', 'Accounting', 'Audit', 'Tax'],
                    'HR': ['HR', 'Recruiter', 'Talent', 'People'],
                    'Product': ['Product', 'PM'],
                    'Operations': ['Operation', 'Supply'],
                    'Design': ['Design', 'UI', 'UX'],
                    'Support': ['Support', 'Customer'],
                    'Legal': ['Legal', 'Compliance'],
                    'Medical': ['Medical', 'Nurse', 'Health', 'Healthcare'],
                    'Education': ['Teacher', 'Examiner', 'Tutor', 'Education'],
                }
                for cat, keywords in category_keywords.items():
                    for kw in keywords:
                        if re.search(r'\b' + re.escape(kw) + r'\b', title, re.IGNORECASE):
                            category = cat
                            break
                    if category:
                        break
            job_info['job_category'] = category

            # 描述
            description = ''
            try:
                desc_match = re.search(r'What you will do\s*(.+?)(?:About the job|Apply before|Qualifications|Benefits|$)', body_text, re.IGNORECASE | re.DOTALL)
                if desc_match:
                    description = desc_match.group(1).strip()
            except:
                pass
            
            if not description:
                try:
                    desc_elem = await page.query_selector('.pb-8 article')
                    if desc_elem:
                        description = await desc_elem.inner_text()
                        description = description.strip() if description else ''
                except:
                    pass
            
            if not description:
                try:
                    paragraphs = re.findall(r'[A-Z][^.!?]*[.!?]', body_text)
                    if paragraphs:
                        description = ' '.join(paragraphs[:10])
                except:
                    pass
            
            job_info['description'] = description[:5000] if description else ''

            # 发布时间
            posted_time = ''
            try:
                posted_label = await page.query_selector('h3:has-text("Posted on")')
                if posted_label:
                    time_elem = await posted_label.evaluate_handle('''(el) => {
                        let next = el.nextElementSibling;
                        while (next) {
                            if (next.tagName === 'TIME') {
                                return next;
                            }
                            next = next.nextElementSibling;
                        }
                        return null;
                    }''')
                    if time_elem:
                        time_text = await time_elem.inner_text()
                        posted_time = time_text.strip() if time_text else ''
                
                if not posted_time:
                    body_text_full = await self._extract_from_body(page)
                    posted_match = re.search(r'Posted\s+on\s*\n?\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})', body_text_full, re.IGNORECASE)
                    if posted_match:
                        posted_time = posted_match.group(1)
            except:
                pass
            job_info['posted_time'] = posted_time

            # 获取申请链接
            apply_url = await self._get_apply_url(page, url)
            job_info['apply_url'] = apply_url

            logger.info(f"    📌 {job_info.get('title')}")
            logger.info(f"      公司: {job_info.get('company', '未知')}")
            if apply_url:
                logger.info(f"      申请链接: {apply_url[:80]}...")

            return job_info

        except Exception as e:
            return None

    async def crawl(self, page_number: int = 1):
        """
        手动爬取指定页码
        page_number: 要爬的页码
        """
        logger.info("=" * 50)
        logger.info("Himalayas 爬虫（手动单页模式）")
        logger.info(f"目标页码: {page_number}")
        logger.info("=" * 50)

        if not self._start_chrome_debug():
            logger.error("无法启动 Chrome，请手动启动")
            return

        browser = None
        context = None
        page = None

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

                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                
                if context.pages:
                    page = context.pages[0]
                else:
                    page = await context.new_page()

                page.set_default_timeout(60000)

                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    window.chrome = { runtime: {} };
                """)

                list_url = f"{self.base_url}/jobs?page={page_number}"
                logger.info(f"访问列表页: {list_url}")
                
                await page.goto(list_url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(5000)

                # 人机验证
                body_text = await page.inner_text('body')
                if 'verifying' in body_text.lower() or '真人' in body_text:
                    logger.warning("=" * 50)
                    logger.warning("⚠️ 检测到人机验证！")
                    logger.warning("请在浏览器中手动完成验证")
                    logger.warning("验证完成后按回车键继续...")
                    logger.warning("=" * 50)
                    input("按回车键继续...")
                    await page.reload()
                    await page.wait_for_timeout(5000)

                # 检查登录
                if not await self._check_login_status(page):
                    if not await self._wait_for_login(page, list_url):
                        return

                await page.wait_for_timeout(3000)

                # 获取所有职位链接
                all_links = await page.query_selector_all('a[href*="/companies/"]')
                
                job_links = []
                seen = set()
                for link in all_links:
                    href = await link.get_attribute('href')
                    if href and '/companies/' in href and '/jobs/' in href:
                        if href.startswith('/'):
                            full_url = f"{self.base_url}{href}"
                        else:
                            full_url = href
                        if full_url not in seen:
                            seen.add(full_url)
                            job_links.append(full_url)

                if not job_links:
                    logger.warning("没有找到职位")
                    return

                logger.info(f"本页找到 {len(job_links)} 个职位")

                page_total = 0
                skip_count = 0
                consecutive_failures = 0

                for idx, full_url in enumerate(job_links, 1):
                    logger.info(f"  ({idx}/{len(job_links)}) 访问: {full_url}")

                    # 检查登录
                    if not await self._check_login_status(page):
                        if not await self._wait_for_login(page, list_url):
                            break

                    detail_page = None
                    try:
                        detail_page = await context.new_page()
                        detail_page.set_default_timeout(60000)
                        
                        await detail_page.goto(full_url, wait_until='domcontentloaded', timeout=45000)
                        
                        if 'login' in detail_page.url or 'signin' in detail_page.url:
                            await detail_page.close()
                            if not await self._wait_for_login(page, list_url):
                                break
                            continue
                        
                        await detail_page.wait_for_timeout(random.randint(2000, 4000))

                        job_info = await self._extract_detail(detail_page, full_url)

                        if not job_info:
                            logger.warning(f"    提取失败，跳过")
                            await detail_page.close()
                            consecutive_failures += 1
                            if consecutive_failures >= 3:
                                logger.warning("  ⚠️ 连续失败3次，等待重新登录...")
                                if not await self._wait_for_login(page, list_url):
                                    break
                                consecutive_failures = 0
                            continue

                        consecutive_failures = 0

                        # ⭐ 按 job_url 去重（数据库）
                        existing = self.session.query(HimalayasJob).filter(
                            HimalayasJob.job_url == full_url
                        ).first()
                        
                        if existing:
                            logger.info(f"    ⏭️ 已存在，跳过")
                            await detail_page.close()
                            skip_count += 1
                            continue

                        if self.save_job(job_info):
                            page_total += 1
                            self.job_data_list.append({
                                'job_url': full_url,
                                'title': job_info.get('title', ''),
                                'apply_url': job_info.get('apply_url', ''),
                                'description': job_info.get('description', '')[:5000],
                                'job_category': job_info.get('job_category', ''),
                                'job_style': job_info.get('job_style', ''),
                                'country': job_info.get('country', ''),
                                'salary': job_info.get('salary', ''),
                                'company': job_info.get('company', ''),
                                'posted_time': job_info.get('posted_time', '')
                            })
                            logger.info(f"    ✅ 已保存 (本页: {page_total})")

                    except PlaywrightTimeoutError as e:
                        logger.error(f"    详情页超时: {e}")
                        consecutive_failures += 1
                    except Exception as e:
                        logger.error(f"    详情页失败: {e}")
                        consecutive_failures += 1
                    finally:
                        if detail_page:
                            try:
                                await detail_page.close()
                            except:
                                pass

                    delay = random.uniform(2, 4)
                    await asyncio.sleep(delay)

                logger.info(f"\n第 {page_number} 页完成！采集 {page_total} 条，跳过 {skip_count} 条重复")

        except Exception as e:
            logger.error(f"爬取失败: {e}")
        finally:
            try:
                if page:
                    await page.close()
                if context:
                    await context.close()
                if browser:
                    await browser.close()
            except:
                pass

        self._export_to_excel(page_number)
        await self.close()

    def _export_to_excel(self, page_number: int = None):
        """导出数据到 data/himalayas/ 目录"""
        try:
            if not self.job_data_list:
                logger.warning("没有数据可导出")
                return

            output_dir = Path(__file__).parent.parent.parent / "data" / "himalayas"
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if page_number:
                filename = output_dir / f"himalayas_jobs_page{page_number}_{timestamp}.xlsx"
            else:
                filename = output_dir / f"himalayas_jobs_{timestamp}.xlsx"

            df = pd.DataFrame(self.job_data_list)
            columns = ['job_url', 'title', 'apply_url', 'description', 
                      'job_category', 'job_style', 'country', 'salary', 
                      'company', 'posted_time']
            df = df[columns]
            
            df.to_excel(str(filename), index=False, engine='openpyxl')
            logger.success(f"📊 数据已导出到: {filename}")
            logger.success(f"📊 共导出 {len(self.job_data_list)} 条数据")

        except Exception as e:
            logger.error(f"导出Excel失败: {e}")

    async def close(self):
        self.session.close()


async def main():
    crawler = HimalayasCrawler()
    try:
        PAGE_NUMBER = 4
        
        await crawler.crawl(page_number=PAGE_NUMBER)
    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())