"""岗位列表、搜索筛选、标准化触发、Excel 导出 API。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_active_user
from database import get_db
from models import CrawlLog, JobRecord, User
from services.exporter import export_jobs_excel
from services.standardizer import StandardizerService

router = APIRouter(prefix="/jobs", tags=["岗位管理"])


@router.get("", response_model=Dict[str, Any])
async def list_jobs(
    task_id: Optional[int] = Query(None, description="按任务筛选"),
    is_standardized: Optional[bool] = Query(None, description="按标准化状态筛选"),
    keyword: Optional[str] = Query(None, description="标题/公司/描述关键词"),
    work_location_type: Optional[str] = Query(None, description="online_remote / offline_office"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """岗位列表分页查询，支持多条件筛选。"""
    stmt = select(JobRecord)
    count_stmt = select(func.count(JobRecord.id))

    filters = []
    if task_id:
        filters.append(JobRecord.task_id == task_id)
    if is_standardized is not None:
        filters.append(JobRecord.is_standardized == is_standardized)
    if work_location_type:
        filters.append(
            JobRecord.standardized_data["task"]["work_location_type（可选，工作地点类型：online_remote/线上远程 或 offline_office/线下办公）"].as_string() == work_location_type
        )
    if keyword:
        like = f"%{keyword}%"
        filters.append(
            (JobRecord.title.ilike(like))
            | (JobRecord.company.ilike(like))
            | (JobRecord.description.ilike(like))
        )

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.order_by(desc(JobRecord.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    jobs = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": j.id,
                "task_id": j.task_id,
                "channel_id": j.channel_id,
                "url": j.url,
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "salary": j.salary,
                "description": j.description[:300] + "..." if len(j.description) > 300 else j.description,
                "is_standardized": j.is_standardized,
                "standardized_at": j.standardized_at.isoformat() if j.standardized_at else None,
                "matched_skills": [
                    {
                        "primary": s.get("primary_cn") or s.get("primary_en", ""),
                        "secondary": s.get("secondary_cn") or s.get("secondary_en", ""),
                        "tertiary": s.get("tertiary_cn") or s.get("tertiary_en", ""),
                    }
                    for s in (j.matched_skills or [])
                ],
                "created_at": j.created_at.isoformat(),
            }
            for j in jobs
        ],
    }


@router.get("/stats", response_model=Dict[str, Any])
async def jobs_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """岗位统计概览。"""
    total_result = await db.execute(select(func.count(JobRecord.id)))
    total = total_result.scalar_one()

    std_result = await db.execute(select(func.count(JobRecord.id)).where(JobRecord.is_standardized == True))
    standardized = std_result.scalar_one()

    task_result = await db.execute(select(func.count(func.distinct(JobRecord.task_id))))
    task_count = task_result.scalar_one()

    return {
        "total": total,
        "standardized": standardized,
        "unstandardized": total - standardized,
        "task_count": task_count,
    }


@router.get("/{job_id}", response_model=Dict[str, Any])
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """岗位详情，包含原始数据与标准化数据。"""
    job = await db.get(JobRecord, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="岗位不存在")
    return {
        "id": job.id,
        "task_id": job.task_id,
        "channel_id": job.channel_id,
        "url": job.url,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "salary": job.salary,
        "description": job.description,
        "raw_data": job.raw_data,
        "is_standardized": job.is_standardized,
        "standardized_at": job.standardized_at.isoformat() if job.standardized_at else None,
        "standardized_data": job.standardized_data,
        "matched_skills": job.matched_skills,
        "created_at": job.created_at.isoformat(),
    }


@router.post("/standardize", response_model=Dict[str, Any])
async def standardize_jobs(
    task_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """触发数据标准化。可指定 task_id，否则全部刷新。"""
    service = StandardizerService(db)
    if task_id:
        stats = await service.standardize_task_jobs(task_id)
    else:
        stats = await service.restandardize_all()
    return {"success": True, "stats": stats}


@router.get("/export")
async def export_excel(
    task_id: Optional[int] = Query(None, description="按任务筛选导出"),
    standardized_only: bool = Query(True, description="仅导出已标准化数据"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """导出匹配导入模板的 Excel 文件。"""
    excel_bytes = await export_jobs_excel(db, task_id=task_id, standardized_only=standardized_only)
    if task_id:
        db.add(CrawlLog(
            task_id=task_id,
            level="info",
            message=f"导出 Excel 完成: {'已标准化数据' if standardized_only else '全部数据'}",
        ))
        await db.commit()
    filename = f"jobs_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
