import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from loguru import logger

from app.crawler.boss import BossCrawler
from app.crawler.hiredchina import HiredChinaCrawler
from app.crawler.chinajoy import ChinaJoyCrawler


async def main():
    args = sys.argv[1:] if len(sys.argv) > 1 else ['boss']
    crawler_name = args[0].lower()
    
    max_pages = 100 
    start_page = 1
    
    if len(args) > 1:
        try:
            max_pages = int(args[1])
        except ValueError:
            logger.warning(f"参数无效，使用默认值: {max_pages}")
    
    if len(args) > 2:
        try:
            start_page = int(args[2])
        except ValueError:
            logger.warning(f"起始页参数无效，使用默认值: {start_page}")
    
    logger.info("=" * 60)
    logger.info("爬虫系统启动")
    logger.info(f"目标: {crawler_name}")
    if crawler_name == 'chinajoy':
        logger.info(f"起始页: {start_page}")
    elif crawler_name == 'boss':
        logger.info(f"滚动次数: {max_pages}")
    logger.info("=" * 60)
    
    if crawler_name == 'boss':
        boss = BossCrawler()
        try:
            await boss.crawl(max_pages=max_pages)
        finally:
            await boss.close()
    
    if crawler_name == 'hiredchina':
        hiredchina = HiredChinaCrawler()
        try:
            await hiredchina.crawl_all_countries()
        finally:
            await hiredchina.close()
    
    if crawler_name == 'chinajoy':
        logger.info("开始爬取 ChinaJoy...")
        chinajoy = ChinaJoyCrawler()
        try:
            await chinajoy.crawl_all_companies(start_page=start_page)
        finally:
            chinajoy.close()
    
    if crawler_name not in ['boss', 'hiredchina', 'chinajoy']:
        logger.error(f"未知参数: {crawler_name}")
        logger.info("使用方法:")
        logger.info("  python main.py boss           # 只爬BOSS（滚动100次）")
        logger.info("  python main.py hiredchina     # 只爬HiredChina")
        logger.info("  python main.py chinajoy       # 只爬ChinaJoy")
    
    logger.info("=" * 60)
    logger.info("爬虫执行完毕！")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.error(f"程序异常: {e}")