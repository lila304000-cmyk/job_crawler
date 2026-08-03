from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ==================== 通用响应 ====================
class ResponseWrapper(BaseModel):
    code: int = 0
    message: str = "success"
    data: Any = None


# ==================== 用户/认证 ====================
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserLogin(BaseModel):
    username: str
    password: str


# ==================== 渠道选择器配置 ====================
class ChannelSelectors(BaseModel):
    list_container: Optional[str] = Field("", description="岗位卡片列表容器选择器")
    job_card: Optional[str] = Field("", description="单个岗位卡片选择器")
    title: Optional[str] = Field("", description="职位名称")
    company: Optional[str] = Field("", description="公司名称")
    location: Optional[str] = Field("", description="工作地点")
    salary: Optional[str] = Field("", description="薪资")
    description: Optional[str] = Field("", description="职位描述")
    detail_link: Optional[str] = Field("a[href]", description="详情页链接")
    detail_title: Optional[str] = Field("h1", description="详情页标题")
    detail_company: Optional[str] = Field("", description="详情页公司")
    detail_location: Optional[str] = Field("", description="详情页地点")
    detail_salary: Optional[str] = Field("", description="详情页薪资")
    detail_description: Optional[str] = Field("", description="详情页描述")
    next_page: Optional[str] = Field("", description="下一页按钮/链接选择器")
    cookie_banner: Optional[str] = Field("", description="Cookie/登录弹窗关闭按钮选择器")
    login_check: Optional[str] = Field("", description="检测登录页的元素选择器")


class ChannelCrawlRules(BaseModel):
    max_pages: int = Field(5, ge=1, le=100)
    max_jobs: int = Field(200, ge=1, le=5000)
    scroll_times: int = Field(3, ge=0, le=100)
    scroll_step: int = Field(800, ge=100, le=2000)
    scroll_delay_ms: int = Field(1500, ge=100, le=10000)
    headless: bool = True
    use_cdp: bool = False
    cdp_url: str = "http://localhost:9222"
    wait_after_goto_ms: int = Field(3000, ge=0, le=30000)
    wait_after_detail_ms: int = Field(3000, ge=0, le=30000)
    random_delay_min: float = Field(1.0, ge=0, le=60)
    random_delay_max: float = Field(3.0, ge=0, le=60)


class ChannelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    site_url: str = Field(..., min_length=1, max_length=500)
    enabled: bool = True
    selectors: ChannelSelectors = Field(default_factory=ChannelSelectors)
    crawl_rules: ChannelCrawlRules = Field(default_factory=ChannelCrawlRules)
    note: str = ""


class ChannelCreate(ChannelBase):
    pass


class ChannelUpdate(ChannelBase):
    name: Optional[str] = None
    site_url: Optional[str] = None


class ChannelOut(ChannelBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== 任务 ====================
class TaskBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    channel_id: int
    max_pages: int = Field(5, ge=1, le=100)
    max_jobs: int = Field(200, ge=1, le=5000)
    use_cdp: bool = False
    cdp_url: str = "http://localhost:9222"
    headless: bool = True
    schedule: str = ""


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    channel_id: Optional[int] = None
    max_pages: Optional[int] = Field(None, ge=1, le=100)
    max_jobs: Optional[int] = Field(None, ge=1, le=5000)
    use_cdp: Optional[bool] = None
    cdp_url: Optional[str] = None
    headless: Optional[bool] = None
    schedule: Optional[str] = None


class TaskOut(TaskBase):
    id: int
    status: str
    last_run_at: Optional[datetime]
    last_run_result: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    channel: Optional[ChannelOut] = None

    class Config:
        from_attributes = True


class TaskRunResult(BaseModel):
    task_id: int
    status: str
    total: int
    saved: int
    duplicated: int
    failed: int
    message: str


# ==================== 日志 ====================
class CrawlLogOut(BaseModel):
    id: int
    task_id: int
    level: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== 岗位记录 ====================
class JobRecordOut(BaseModel):
    id: int
    task_id: int
    channel_id: int
    url: str
    title: str
    company: str
    location: str
    salary: str
    description: str
    raw_data: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
