from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import get_async_session
from models.models import hrs, user
from auth.auth import superuser_required, current_user
from api.utils import is_hr

router = APIRouter(prefix="/hr", tags=["hr"])


@router.get("/")
async def list_hr(session: AsyncSession = Depends(get_async_session), admin=Depends(superuser_required)):
    q = select(hrs.c.user_id)
    r = await session.execute(q)
    items = [row.user_id for row in r.fetchall()]
    return {"hrs": items}


@router.post("/")
async def add_hr(user_id: int, session: AsyncSession = Depends(get_async_session), admin=Depends(superuser_required)):
    # Проверим что пользователь существует
    q = select(user).where(user.c.id == user_id)
    r = await session.execute(q)
    if r.fetchone() is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    await session.execute(hrs.insert().values(user_id=user_id))
    await session.commit()
    return {"added": user_id}


@router.delete("/{user_id}")
async def remove_hr(user_id: int, session: AsyncSession = Depends(get_async_session), admin=Depends(superuser_required)):
    await session.execute(delete(hrs).where(hrs.c.user_id == user_id))
    await session.commit()
    return {"removed": user_id}


@router.get('/me')
async def hr_me(session: AsyncSession = Depends(get_async_session), user=Depends(current_user)):
    """Возвращает роль HR для текущего пользователя."""
    return {"is_hr": await is_hr(session, user.id)}
