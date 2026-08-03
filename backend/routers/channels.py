from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from auth import get_current_user
from models import User, Channel
from schemas import ChannelCreate, ChannelUpdate, ChannelOut, ResponseWrapper

router = APIRouter(prefix="/channels", tags=["渠道管理"])


@router.get("", response_model=ResponseWrapper)
async def list_channels(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Channel).offset(skip).limit(limit).order_by(Channel.created_at.desc()))
    items = result.scalars().all()
    total_result = await db.execute(select(Channel))
    total = len(total_result.scalars().all())
    return ResponseWrapper(data={"items": [ChannelOut.model_validate(i) for i in items], "total": total})


@router.get("/{channel_id}", response_model=ResponseWrapper)
async def get_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="渠道不存在")
    return ResponseWrapper(data=ChannelOut.model_validate(channel))


@router.post("", response_model=ResponseWrapper, status_code=status.HTTP_201_CREATED)
async def create_channel(
    payload: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    channel = Channel(
        name=payload.name,
        site_url=payload.site_url,
        enabled=payload.enabled,
        selectors=payload.selectors.model_dump(),
        crawl_rules=payload.crawl_rules.model_dump(),
        note=payload.note,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return ResponseWrapper(data=ChannelOut.model_validate(channel))


@router.put("/{channel_id}", response_model=ResponseWrapper)
async def update_channel(
    channel_id: int,
    payload: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="渠道不存在")

    update_data = payload.model_dump(exclude_unset=True)
    if "selectors" in update_data:
        update_data["selectors"] = update_data["selectors"].model_dump()
    if "crawl_rules" in update_data:
        update_data["crawl_rules"] = update_data["crawl_rules"].model_dump()

    for key, value in update_data.items():
        setattr(channel, key, value)

    await db.commit()
    await db.refresh(channel)
    return ResponseWrapper(data=ChannelOut.model_validate(channel))


@router.delete("/{channel_id}", response_model=ResponseWrapper)
async def delete_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="渠道不存在")
    await db.delete(channel)
    await db.commit()
    return ResponseWrapper(data={"deleted": True})
