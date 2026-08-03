from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from auth import get_current_user
from models import Channel, CrawlLog, Task, User
from schemas import (
    ResponseWrapper,
    TaskCreate,
    TaskOut,
    TaskRunResult,
    TaskUpdate,
)
from services.scraper import run_scraper

router = APIRouter(prefix="/tasks", tags=["采集任务"])


@router.get("", response_model=ResponseWrapper)
async def list_tasks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Task).offset(skip).limit(limit).order_by(Task.created_at.desc())
    )
    items = result.scalars().all()
    return ResponseWrapper(data={
        "items": [TaskOut.model_validate(i) for i in items],
        "total": len(items),
    })


@router.get("/{task_id}", response_model=ResponseWrapper)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return ResponseWrapper(data=TaskOut.model_validate(task))


@router.post("", response_model=ResponseWrapper, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    channel = await db.get(Channel, payload.channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="渠道不存在")

    task = Task(
        name=payload.name,
        channel_id=payload.channel_id,
        max_pages=payload.max_pages,
        max_jobs=payload.max_jobs,
        use_cdp=payload.use_cdp,
        cdp_url=payload.cdp_url,
        headless=payload.headless,
        schedule=payload.schedule,
        status="idle",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return ResponseWrapper(data=TaskOut.model_validate(task))


@router.put("/{task_id}", response_model=ResponseWrapper)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    update_data = payload.model_dump(exclude_unset=True)
    if "channel_id" in update_data:
        channel = await db.get(Channel, update_data["channel_id"])
        if not channel:
            raise HTTPException(status_code=404, detail="渠道不存在")

    for key, value in update_data.items():
        setattr(task, key, value)

    await db.commit()
    await db.refresh(task)
    return ResponseWrapper(data=TaskOut.model_validate(task))


@router.delete("/{task_id}", response_model=ResponseWrapper)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    await db.delete(task)
    await db.commit()
    return ResponseWrapper(data={"deleted": True})


@router.post("/{task_id}/run", response_model=ResponseWrapper)
async def run_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status == "running":
        raise HTTPException(status_code=400, detail="任务正在运行中")

    channel = await db.get(Channel, task.channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="关联渠道不存在")

    # 同步执行爬虫（后续可改为后台任务）
    result_data = await run_scraper(db, task.id, channel.id)
    return ResponseWrapper(data=result_data)


@router.get("/{task_id}/logs", response_model=ResponseWrapper)
async def list_task_logs(
    task_id: int,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CrawlLog)
        .where(CrawlLog.task_id == task_id)
        .order_by(CrawlLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return ResponseWrapper(data={
        "items": [
            {
                "id": log.id,
                "task_id": log.task_id,
                "level": log.level,
                "message": log.message,
                "created_at": log.created_at,
            }
            for log in logs
        ],
        "total": len(logs),
    })
