import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.db import engine
from app.database import models

def init_db():
    """创建所有数据库表"""
    models.Base.metadata.create_all(bind=engine)
    print("✅ 所有数据库表创建成功！")
    print("✅ 已创建的表: boss_jobs, hiredchina_jobs, himalayas_jobs, chinajoy_companies")

if __name__ == "__main__":
    init_db()