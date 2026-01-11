from datetime import datetime, date as date_cls
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional
from sqlalchemy import select, insert, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import get_async_session
from models.models import locations, location_days, location_day_owners, owner
from auth.auth import current_user
from api.utils import is_hr, is_director_of_location

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/{location_id}/assignments")
async def get_location_assignments(location_id: int, day: Optional[str] = Query(None), session: AsyncSession = Depends(get_async_session), user=Depends(current_user)):
    # day as YYYY-MM-DD, default today
    if day:
        try:
            req_day = datetime.strptime(day, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="Неверный формат даты, ожидается YYYY-MM-DD")
    else:
        req_day = datetime.now().date()

    # Проверка доступа: superuser, HR или директор данного склада
    if not (getattr(user, 'is_superuser', False) or await is_hr(session, user.id) or await is_director_of_location(session, user.id, location_id)):
        raise HTTPException(status_code=403, detail="Нет доступа к данным складов")

    # Ensure there is a location_day for requested day; may copy from previous day
    from api.utils import ensure_location_day_from_prev
    ld_id = await ensure_location_day_from_prev(session, location_id, req_day)
    if ld_id is None:
        # no previous data to copy and nothing exists
        return {"day": str(req_day), "owners": []}

    # fetch owners for the ensured day
    q5 = select(owner.c.id, owner.c.name).select_from(owner.join(location_day_owners, owner.c.id == location_day_owners.c.owner_id)).where(location_day_owners.c.location_day_id == ld_id)
    res5 = await session.execute(q5)
    owners = [dict(r._mapping) for r in res5.fetchall()]
    return {"day": str(req_day), "owners": owners}

    # Если запись существует — вернуть владельцев
    q5 = select(owner.c.id, owner.c.name).select_from(owner.join(location_day_owners, owner.c.id == location_day_owners.c.owner_id)).where(location_day_owners.c.location_day_id == ld.id)
    res5 = await session.execute(q5)
    owners = [dict(r._mapping) for r in res5.fetchall()]
    return {"day": str(req_day), "owners": owners}


@router.get('/all')
async def list_all_locations(session: AsyncSession = Depends(get_async_session)):
    """Получить список всех активных локаций (без авторизации)"""
    q = select(locations.c.id, locations.c.location_name)
    r = await session.execute(q)
    items = [dict(row._mapping) for row in r.fetchall()]
    return items


@router.get('/list')
async def list_locations(session: AsyncSession = Depends(get_async_session), user=Depends(current_user)):
    # доступ: superuser или HR
    from api.utils import is_hr
    if not (getattr(user, 'is_superuser', False) or await is_hr(session, user.id)):
        raise HTTPException(status_code=403, detail='Нет доступа')
    q = select(locations.c.id, locations.c.location_name)
    r = await session.execute(q)
    items = [dict(row._mapping) for row in r.fetchall()]
    return {"locations": items}


@router.post("/{location_id}/assignments")
async def set_location_assignments(location_id: int, owner_ids: List[int] = Body(..., embed=False), day: Optional[str] = Query(None), session: AsyncSession = Depends(get_async_session), user=Depends(current_user)):
    # day as YYYY-MM-DD, default today
    if day:
        try:
            req_day = datetime.strptime(day, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="Неверный формат даты, ожидается YYYY-MM-DD")
    else:
        req_day = datetime.now().date()

    today = datetime.now().date()
    # Проверка доступа: superuser, HR или директор данного склада
    if not (getattr(user, 'is_superuser', False) or await is_hr(session, user.id) or await is_director_of_location(session, user.id, location_id)):
        raise HTTPException(status_code=403, detail="Нет доступа для изменения назначений")

    if req_day < today:
        # Разрешаем изменять назначение для прошлых дней суперпользователю и HR.
        # Директора не имеют прав менять прошлые дни через этот endpoint.
        if not (getattr(user, 'is_superuser', False) or await is_hr(session, user.id)):
            raise HTTPException(status_code=400, detail="Нельзя изменять назначение для прошлых дней")

    # Получаем или создаем запись location_day
    q = select(location_days).where(location_days.c.location_id == location_id, location_days.c.day == req_day)
    res = await session.execute(q)
    ld = res.fetchone()

    if ld is None:
        ins = location_days.insert().values(location_id=location_id, day=req_day, finalized=False).returning(location_days.c.id)
        result = await session.execute(ins)
        try:
            location_day_id = result.scalar_one()
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to create location day")
    else:
        # Проверяем finalized
        if ld.finalized:
            raise HTTPException(status_code=400, detail="Назначение для этого дня зафиксировано и не может быть изменено")
        location_day_id = ld.id

    # Очистим текущих владельцев и добавим новые
    await session.execute(delete(location_day_owners).where(location_day_owners.c.location_day_id == location_day_id))
    if owner_ids:
        data = [{"location_day_id": location_day_id, "owner_id": oid} for oid in owner_ids]
        await session.execute(location_day_owners.insert(), data)

    await session.commit()
    return {"day": str(req_day), "owners_set": owner_ids}
