"""API endpoints for managing Channels, Routing Rules, and Muting Silences."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.alerting.channels import get_channel_instance
from app.core.metadata_db import get_db
from app.models.channel import Channel, ChannelCreate, ChannelResponse, ChannelUpdate
from app.models.routing_rule import (
    RoutingRule,
    RoutingRuleCreate,
    RoutingRuleResponse,
    RoutingRuleUpdate,
)
from app.models.silence import Silence, SilenceCreate, SilenceResponse, SilenceUpdate

router = APIRouter(prefix="/api", tags=["alerting"])


# ============================================================================
# Channels CRUD
# ============================================================================


@router.get("/channels", response_model=list[ChannelResponse])
async def list_channels(db: AsyncSession = Depends(get_db)) -> list[Channel]:
    """Retrieve all notification channels."""
    stmt = select(Channel).order_by(Channel.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/channels", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    channel_in: ChannelCreate, db: AsyncSession = Depends(get_db)
) -> Channel:
    """Create a new notification channel."""
    channel = Channel(**channel_in.model_dump())
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.patch("/channels/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: int,
    channel_in: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
) -> Channel:
    """Update an existing channel."""
    stmt = select(Channel).where(Channel.id == channel_id)
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel with ID {channel_id} not found",
        )

    update_data = channel_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(channel, field, value)

    await db.commit()
    await db.refresh(channel)
    return channel


@router.delete("/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a channel."""
    stmt = select(Channel).where(Channel.id == channel_id)
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel with ID {channel_id} not found",
        )

    await db.delete(channel)
    await db.commit()


@router.post("/channels/{channel_id}/test")
async def test_channel(
    channel_id: int, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Execute a connection test send for a channel."""
    stmt = select(Channel).where(Channel.id == channel_id)
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel with ID {channel_id} not found",
        )

    try:
        sender = get_channel_instance(channel.type, channel.config)
        test_message = (
            "🔔 Sentinel Notification Test\n"
            "If you receive this, your notification channel is working correctly."
        )
        await sender.send(test_message, subject="Sentinel Connection Test")
        return {"success": True, "message": "Test notification sent successfully"}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Test failed: {exc}",
        ) from exc


# ============================================================================
# Routing Rules CRUD
# ============================================================================


@router.get("/routing_rules", response_model=list[RoutingRuleResponse])
async def list_routing_rules(db: AsyncSession = Depends(get_db)) -> list[RoutingRule]:
    """Retrieve all routing rules, with eager loaded channels."""
    stmt = select(RoutingRule).options(selectinload(RoutingRule.channel)).order_by(RoutingRule.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post(
    "/routing_rules",
    response_model=RoutingRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_routing_rule(
    rule_in: RoutingRuleCreate, db: AsyncSession = Depends(get_db)
) -> RoutingRule:
    """Create a new routing rule."""
    # Verify channel exists first
    channel_stmt = select(Channel).where(Channel.id == rule_in.channel_id)
    channel_res = await db.execute(channel_stmt)
    if not channel_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target channel with ID {rule_in.channel_id} does not exist",
        )

    rule = RoutingRule(**rule_in.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    
    # Reload to populate channel relationship
    stmt = (
        select(RoutingRule)
        .options(selectinload(RoutingRule.channel))
        .where(RoutingRule.id == rule.id)
    )
    result = await db.execute(stmt)
    return result.scalar_one()


@router.patch("/routing_rules/{rule_id}", response_model=RoutingRuleResponse)
async def update_routing_rule(
    rule_id: int,
    rule_in: RoutingRuleUpdate,
    db: AsyncSession = Depends(get_db),
) -> RoutingRule:
    """Update an existing routing rule."""
    stmt = (
        select(RoutingRule)
        .options(selectinload(RoutingRule.channel))
        .where(RoutingRule.id == rule_id)
    )
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Routing rule with ID {rule_id} not found",
        )

    if rule_in.channel_id is not None:
        channel_stmt = select(Channel).where(Channel.id == rule_in.channel_id)
        channel_res = await db.execute(channel_stmt)
        if not channel_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target channel with ID {rule_in.channel_id} does not exist",
            )

    update_data = rule_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/routing_rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_routing_rule(
    rule_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a routing rule."""
    stmt = select(RoutingRule).where(RoutingRule.id == rule_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Routing rule with ID {rule_id} not found",
        )

    await db.delete(rule)
    await db.commit()


# ============================================================================
# Silences CRUD
# ============================================================================


@router.get("/silences", response_model=list[SilenceResponse])
async def list_silences(db: AsyncSession = Depends(get_db)) -> list[Silence]:
    """Retrieve all silence muting rules."""
    stmt = select(Silence).order_by(Silence.start_time.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/silences", response_model=SilenceResponse, status_code=status.HTTP_201_CREATED)
async def create_silence(
    silence_in: SilenceCreate, db: AsyncSession = Depends(get_db)
) -> Silence:
    """Create a new silence muting rule."""
    silence = Silence(**silence_in.model_dump())
    db.add(silence)
    await db.commit()
    await db.refresh(silence)
    return silence


@router.patch("/silences/{silence_id}", response_model=SilenceResponse)
async def update_silence(
    silence_id: int,
    silence_in: SilenceUpdate,
    db: AsyncSession = Depends(get_db),
) -> Silence:
    """Update an existing silence rule."""
    stmt = select(Silence).where(Silence.id == silence_id)
    result = await db.execute(stmt)
    silence = result.scalar_one_or_none()
    if not silence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Silence with ID {silence_id} not found",
        )

    update_data = silence_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(silence, field, value)

    await db.commit()
    await db.refresh(silence)
    return silence


@router.delete("/silences/{silence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_silence(
    silence_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a silence rule."""
    stmt = select(Silence).where(Silence.id == silence_id)
    result = await db.execute(stmt)
    silence = result.scalar_one_or_none()
    if not silence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Silence with ID {silence_id} not found",
        )

    await db.delete(silence)
    await db.commit()
