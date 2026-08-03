from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="渠道名称")
    site_url = Column(String(500), nullable=False, comment="站点入口URL")
    enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    selectors = Column(JSON, default=dict, comment="CSS选择器配置")
    crawl_rules = Column(JSON, default=dict, comment="爬取规则: max_pages/max_jobs/scroll_times/headless/use_cdp等")
    note = Column(Text, default="", comment="备注")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tasks = relationship("Task", back_populates="channel", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="任务名称")
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False, comment="关联渠道")
    status = Column(String(20), default="idle", comment="idle/running/success/failed")
    max_pages = Column(Integer, default=5, comment="最大列表页数")
    max_jobs = Column(Integer, default=200, comment="最大采集岗位数")
    use_cdp = Column(Boolean, default=False, comment="是否连接Chrome调试端口")
    cdp_url = Column(String(255), default="http://localhost:9222", comment="CDP地址")
    headless = Column(Boolean, default=True, comment="是否无头模式")
    schedule = Column(String(100), default="", comment="定时规则(Cron)")
    last_run_at = Column(DateTime, nullable=True, comment="上次运行时间")
    last_run_result = Column(JSON, default=dict, comment="上次运行结果统计")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    channel = relationship("Channel", back_populates="tasks")
    jobs = relationship("JobRecord", back_populates="task", cascade="all, delete-orphan")
    logs = relationship("CrawlLog", back_populates="task", cascade="all, delete-orphan")


class JobRecord(Base):
    __tablename__ = "job_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, comment="关联任务")
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False, comment="关联渠道")
    url = Column(String(1000), nullable=False, comment="岗位链接")
    url_hash = Column(String(64), index=True, nullable=False, comment="URL哈希用于去重")
    title = Column(String(500), default="", comment="职位名称")
    company = Column(String(255), default="", comment="公司名称")
    location = Column(String(255), default="", comment="工作地点")
    salary = Column(String(255), default="", comment="薪资")
    description = Column(Text, default="", comment="职位描述")
    raw_data = Column(JSON, default=dict, comment="原始爬取数据")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    task = relationship("Task", back_populates="jobs")

    __table_args__ = (
        Index("idx_job_task_url", "task_id", "url_hash"),
    )


class CrawlLog(Base):
    __tablename__ = "crawl_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, comment="关联任务")
    level = Column(String(20), default="info", comment="日志级别")
    message = Column(Text, default="", comment="日志内容")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    task = relationship("Task", back_populates="logs")
