from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class BossJob(Base):
    """BOSS直聘职位表"""
    __tablename__ = "boss_jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), unique=True, nullable=False, comment="职位ID")
    title = Column(String(255), comment="职位名称")
    company = Column(String(255), comment="公司名称")
    salary = Column(String(100), comment="薪资范围")
    experience = Column(String(100), comment="经验要求")
    education = Column(String(100), comment="学历要求")
    location = Column(String(255), comment="工作地点")
    description = Column(Text, comment="职位描述")
    company_url = Column(String(500), comment="公司链接")
    job_url = Column(String(500), comment="职位链接")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
   

class HiredChinaJob(Base):
    """HiredChina职位表"""
    __tablename__ = "hiredchina_jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_url = Column(String(500), unique=True, nullable=False, comment="职位链接")
    title = Column(String(255), comment="职位名称")
    company = Column(String(255), comment="公司名称")
    country = Column(String(100), comment="国家")
    salary = Column(String(100), comment="薪资")
    job_type = Column(String(100), comment="工作类型")
    description = Column(Text, comment="职位描述")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


class HimalayasJob(Base):
    """Himalayas职位表"""
    __tablename__ = "himalayas_jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_url = Column(String(500), unique=True, nullable=False, comment="职位链接")
    title = Column(String(255), comment="职位名称")
    apply_url = Column(String(500), comment="申请链接")
    description = Column(Text, comment="职位描述")
    job_category = Column(String(500), comment="职位分类")
    job_style = Column(String(255), comment="工作类型")
    country = Column(Text, comment="国家")
    salary = Column(String(100), comment="薪资")
    company = Column(String(255), comment="公司名称")
    posted_time = Column(String(100), comment="发布时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


class ChinaJoyCompany(Base):
    """ChinaJoy 参展商信息表"""
    __tablename__ = "chinajoy_companies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    detail_url = Column(String(500), unique=True, nullable=False, comment="详情链接")
    booth_code = Column(String(50), comment="展位号")
    company_name = Column(String(255), comment="公司名称")
    website = Column(String(500), comment="公司网址")
    address = Column(String(500), comment="公司地址")
    company_scale = Column(String(100), comment="公司规模")
    founded_year = Column(String(50), comment="成立时间")
    previous_revenue = Column(String(100), comment="往年收入")
    description = Column(Text, comment="公司简介")
    logo = Column(String(500), comment="公司logo")