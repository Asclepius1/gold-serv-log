from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Dict, Any
from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.utils import is_hr

from models.db import get_async_session
from models.models import warehouse_directors, warehouse_directors_history, locations, location_days, location_day_stats, location_day_owners, user
from auth.auth import current_user
from auth.db import User

router = APIRouter(prefix="/directors", tags=["directors"])


async def get_director_location(session: AsyncSession, user_id: int):
    q = select(warehouse_directors).where(warehouse_directors.c.user_id == user_id)
    r = await session.execute(q)
    wd = r.fetchone()
    return wd


@router.get("/me")
async def director_me(session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    # Проверяем, к какому складу привязан текущий пользователь
    wd = await get_director_location(session, user_obj.id)
    if wd is None:
        raise HTTPException(status_code=403, detail="Вы не являетесь директором склада")

    # Получаем локацию
    q_loc = select(locations).where(locations.c.id == wd.location_id)
    rloc = await session.execute(q_loc)
    loc = rloc.fetchone()

    # Получаем статистику за сегодня (создадим, если нет)
    today = datetime.now().date()
    q_day = select(location_days).where(location_days.c.location_id == wd.location_id, location_days.c.day == today)
    rday = await session.execute(q_day)
    ld = rday.fetchone()
    if ld is None:
        # создаём запись дня
        ins = location_days.insert().values(location_id=wd.location_id, day=today, finalized=False).returning(location_days.c.id)
        res_ins = await session.execute(ins)
        try:
            day_id = res_ins.scalar_one()
        except Exception:
            await session.commit()
            q_get = select(location_days.c.id).where(location_days.c.location_id == wd.location_id, location_days.c.day == today).order_by(location_days.c.id.desc()).limit(1)
            rr = await session.execute(q_get)
            row = rr.fetchone()
            day_id = row._mapping['id'] if row is not None else None
    else:
        day_id = ld.id

    q_stats = select(location_day_stats).where(location_day_stats.c.location_day_id == day_id)
    rstats = await session.execute(q_stats)
    stats = rstats.fetchone()
    if stats is None:
        # создаём пустую статистику по умолчанию
        await session.execute(location_day_stats.insert().values(location_day_id=day_id))
        await session.commit()
        q_stats2 = await session.execute(select(location_day_stats).where(location_day_stats.c.location_day_id == day_id))
        stats = q_stats2.fetchone()

    return {
        "location": dict(loc._mapping) if loc else None,
        "day": str(today),
        "stats": dict(stats._mapping) if stats else None,
    }


@router.get("/me/stats")
async def get_director_stats(day: Optional[str] = Query(None), session: AsyncSession = Depends(get_async_session), user_obj: User = Depends(current_user)):
    """Получить статистику текущего директора за день."""
    wd = await get_director_location(session, user_obj.id)
    if wd is None:
        raise HTTPException(status_code=403, detail="Вы не являетесь директором склада")

    # Парсим день (если не указан — сегодня)
    if day:
        try:
            req_day = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты, ожидается YYYY-MM-DD")
    else:
        req_day = datetime.now().date()

    location_id = wd.location_id

    # Получаем или создаём запись location_day
    from api.utils import ensure_location_day_from_prev
    ld_id = await ensure_location_day_from_prev(session, location_id, req_day)
    if ld_id is None:
        await session.commit()
        return {"day": str(req_day), "stats": None}

    # Получаем статистику (только последнюю запись для этого дня)
    q_stats = select(location_day_stats).where(location_day_stats.c.location_day_id == ld_id).order_by(location_day_stats.c.id.desc()).limit(1)
    rstats = await session.execute(q_stats)
    stats = rstats.fetchone()

    await session.commit()
    return {"day": str(req_day), "stats": dict(stats._mapping) if stats else None}


@router.post("/me/stats")
async def update_stats(location_id: Optional[int] = None, day: Optional[str] = Query(None), arrived_actual: Optional[int] = None, expected: Optional[int] = None, outsourcing: Optional[int] = None, overtime: Optional[int] = None, lunch: Optional[int] = None, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    wd = await get_director_location(session, user_obj.id)
    # Проверка роли: если пользователь директор — он должен быть директором этого склада.
    # HR может редактировать статистику за любые прошедшие дни.
    is_hr_user = await is_hr(session, user_obj.id)
    if not is_hr_user and wd is None:
        raise HTTPException(status_code=403, detail="Вы не являетесь директором склада")

    # Парсим день (если не указан — сегодня)
    if day:
        try:
            req_day = datetime.strptime(day, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="Неверный формат даты, ожидается YYYY-MM-DD")
    else:
        req_day = datetime.now().date()

    # Если пользователь директор, ограничим его правами (директор не может менять прошлые дни)
    if not is_hr_user:
        today = datetime.now().date()
        if req_day < today:
            raise HTTPException(status_code=400, detail="Директор не может изменять прошедшие дни")

    # Определяем location_id: если это директор — его локация, если HR — location_id должен быть передан
    if not is_hr_user:
        location_id = wd.location_id
    else:
        if location_id is None:
            raise HTTPException(status_code=400, detail="Для HR нужно указать параметр location_id")

    q_day = select(location_days).where(location_days.c.location_id == location_id, location_days.c.day == req_day)
    rday = await session.execute(q_day)
    ld = rday.fetchone()
    if ld is None:
        ins = location_days.insert().values(location_id=location_id, day=req_day, finalized=False).returning(location_days.c.id)
        res_ins = await session.execute(ins)
        try:
            location_day_id = res_ins.scalar_one()
        except Exception:
            await session.commit()
            q_get = select(location_days.c.id).where(location_days.c.location_id == location_id, location_days.c.day == req_day).order_by(location_days.c.id.desc()).limit(1)
            rr = await session.execute(q_get)
            row = rr.fetchone()
            location_day_id = row._mapping['id'] if row is not None else None
    else:
        # Если день зафиксирован, директор не может менять; HR может менять даже зафиксированные дни
        if ld.finalized and not is_hr_user:
            raise HTTPException(status_code=400, detail="День зафиксирован и не может быть изменён")
        location_day_id = ld.id

    # Получаем или создаём статистику
    q_stats = select(location_day_stats).where(location_day_stats.c.location_day_id == location_day_id)
    rstats = await session.execute(q_stats)
    stats = rstats.fetchone()
    if stats is None:
        await session.execute(location_day_stats.insert().values(location_day_id=location_day_id))
        await session.commit()
        rstats2 = await session.execute(select(location_day_stats).where(location_day_stats.c.location_day_id == location_day_id))
        stats = rstats2.fetchone()

    update_values = {}
    if arrived_actual is not None:
        update_values['arrived_actual'] = arrived_actual
    if expected is not None:
        update_values['expected'] = expected
    if outsourcing is not None:
        update_values['outsourcing'] = outsourcing
    if overtime is not None:
        update_values['overtime'] = overtime
    if lunch is not None:
        update_values['lunch'] = lunch

    if update_values:
        await session.execute(location_day_stats.update().where(location_day_stats.c.id == stats.id).values(**update_values))
        await session.commit()

    q_final = await session.execute(select(location_day_stats).where(location_day_stats.c.id == stats.id))
    updated = q_final.fetchone()
    return {"day": str(req_day), "stats": dict(updated._mapping) if updated else None}


@router.get('/list')
async def list_directors(day: Optional[str] = Query(None), session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    """Возвращает список всех директоров (доступно для HR и суперпользователя).
    Если указана дата, возвращает директоров на ту дату из истории, иначе текущих."""
    from api.utils import is_hr
    if not (getattr(user_obj, 'is_superuser', False) or await is_hr(session, user_obj.id)):
        raise HTTPException(status_code=403, detail='Нет доступа')
    
    # Parse day parameter
    if day:
        try:
            req_day = datetime.strptime(day, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="Неверный формат даты, ожидается YYYY-MM-DD")
    else:
        req_day = None
    
    if req_day:
        # Get directors from history for the specified day
        q = select(
            warehouse_directors_history.c.user_id,
            warehouse_directors_history.c.location_id,
            user.c.name.label('user_name'),
            user.c.email.label('user_email'),
            locations.c.location_name,
        ).select_from(
            warehouse_directors_history.join(user, warehouse_directors_history.c.user_id == user.c.id).join(locations, warehouse_directors_history.c.location_id == locations.c.id)
        ).where(warehouse_directors_history.c.day == req_day)
        
        r = await session.execute(q)
        items = [dict(row._mapping) for row in r.fetchall()]
        
        # If no history records found for this day, fallback to current directors
        if not items:
            q_current = select(
                warehouse_directors.c.user_id,
                warehouse_directors.c.location_id,
                warehouse_directors.c.is_active,
                user.c.name.label('user_name'),
                user.c.email.label('user_email'),
                locations.c.location_name,
            ).select_from(
                warehouse_directors.join(user, warehouse_directors.c.user_id == user.c.id).join(locations, warehouse_directors.c.location_id == locations.c.id)
            )
            r = await session.execute(q_current)
            items = [dict(row._mapping) for row in r.fetchall()]
    else:
        # Get current directors (from warehouse_directors table)
        q = select(
            warehouse_directors.c.user_id,
            warehouse_directors.c.location_id,
            warehouse_directors.c.is_active,
            user.c.name.label('user_name'),
            user.c.email.label('user_email'),
            locations.c.location_name,
        ).select_from(
            warehouse_directors.join(user, warehouse_directors.c.user_id == user.c.id).join(locations, warehouse_directors.c.location_id == locations.c.id)
        )
        
        r = await session.execute(q)
        items = [dict(row._mapping) for row in r.fetchall()]
    
    return {"directors": items}


@router.get('/{location_id}/stats')
async def get_location_stats_by_location(location_id: int, day: Optional[str] = Query(None), session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    """Получить статистику локации за конкретный день (для HR/суперпользователя)."""
    from api.utils import is_hr
    if not (getattr(user_obj, 'is_superuser', False) or await is_hr(session, user_obj.id)):
        raise HTTPException(status_code=403, detail='Нет доступа')

    if day:
        try:
            req_day = datetime.strptime(day, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="Неверный формат даты, ожидается YYYY-MM-DD")
    else:
        req_day = datetime.now().date()

    # Получаем запись location_day
    # Ensure location_day exists (may copy from previous day)
    from api.utils import ensure_location_day_from_prev
    ld_id = await ensure_location_day_from_prev(session, location_id, req_day)
    if ld_id is None:
        return {"day": str(req_day), "stats": None}

    # get location_day record
    q_day = select(location_days).where(location_days.c.id == ld_id)
    rday = await session.execute(q_day)
    ld = rday.fetchone()

    # Получаем статистику (только последнюю запись для этого дня)
    q_stats = select(location_day_stats).where(location_day_stats.c.location_day_id == ld.id).order_by(location_day_stats.c.id.desc()).limit(1)
    rstats = await session.execute(q_stats)
    stats = rstats.fetchone()

    return {"day": str(req_day), "stats": dict(stats._mapping) if stats else None}


@router.post('/{location_id}/stats')
async def update_location_stats_by_location(location_id: int, day: Optional[str] = Query(None), arrived_actual: Optional[int] = None, expected: Optional[int] = None, outsourcing: Optional[int] = None, overtime: Optional[int] = None, lunch: Optional[int] = None, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    """Обновить статистику локации (для HR/суперпользователя)."""
    from api.utils import is_hr
    is_hr_user = await is_hr(session, user_obj.id)
    is_superuser = getattr(user_obj, 'is_superuser', False)
    
    if not (is_superuser or is_hr_user):
        raise HTTPException(status_code=403, detail='Нет доступа')

    if day:
        try:
            req_day = datetime.strptime(day, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="Неверный формат даты, ожидается YYYY-MM-DD")
    else:
        req_day = datetime.now().date()

    # HR разрешено менять прошедшие дни; директор (в /me/stats) всё равно ограничен выше.

    # Получаем или создаём запись location_day
    q = select(location_days).where(location_days.c.location_id == location_id, location_days.c.day == req_day)
    res = await session.execute(q)
    ld = res.fetchone()

    if ld is None:
        ins = location_days.insert().values(location_id=location_id, day=req_day, finalized=False).returning(location_days.c.id)
        result = await session.execute(ins)
        try:
            location_day_id = result.scalar_one()
        except Exception:
            await session.commit()
            q_get = select(location_days.c.id).where(location_days.c.location_id == location_id, location_days.c.day == req_day).order_by(location_days.c.id.desc()).limit(1)
            rr = await session.execute(q_get)
            row = rr.fetchone()
            location_day_id = row._mapping['id'] if row is not None else None
    else:
        if ld.finalized and not (is_superuser or is_hr_user):
            raise HTTPException(status_code=400, detail="День зафиксирован")
        location_day_id = ld.id

    # Получаем или создаём статистику
    q_stats = select(location_day_stats).where(location_day_stats.c.location_day_id == location_day_id)
    rstats = await session.execute(q_stats)
    stats = rstats.fetchone()
    if stats is None:
        await session.execute(location_day_stats.insert().values(location_day_id=location_day_id))
        await session.commit()
        rstats2 = await session.execute(select(location_day_stats).where(location_day_stats.c.location_day_id == location_day_id))
        stats = rstats2.fetchone()

    # Обновляем только переданные поля
    update_values = {}
    if arrived_actual is not None:
        update_values['arrived_actual'] = arrived_actual
    if expected is not None:
        update_values['expected'] = expected
    if outsourcing is not None:
        update_values['outsourcing'] = outsourcing
    if overtime is not None:
        update_values['overtime'] = overtime
    if lunch is not None:
        update_values['lunch'] = lunch

    if update_values:
        await session.execute(location_day_stats.update().where(location_day_stats.c.id == stats.id).values(**update_values))
        await session.commit()

    q_final = await session.execute(select(location_day_stats).where(location_day_stats.c.id == stats.id))
    updated = q_final.fetchone()
    return {"day": str(req_day), "stats": dict(updated._mapping) if updated else None}


@router.get('/director/dashboard')
async def director_dashboard(session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    """Страница для директора склада со статистикой только своего склада.
    Показывает названиие склада, владельцев, работников за последние 5 дней, статистику."""
    
    # Проверяем, что пользователь директор
    wd = await get_director_location(session, user_obj.id)
    if wd is None:
        raise HTTPException(status_code=403, detail="Вы не являетесь директором склада")
    
    location_id = wd.location_id
    
    # Получаем информацию о локации
    q_loc = select(locations).where(locations.c.id == location_id)
    r_loc = await session.execute(q_loc)
    loc = r_loc.fetchone()
    
    if not loc:
        raise HTTPException(status_code=404, detail="Локация не найдена")
    
    # Получаем владельцев, привязанных к этому складу
    from models.models import location_day_owners, owner
    today = datetime.now().date()
    
    # Получаем последний день для этого склада (или создаём)
    from api.utils import ensure_location_day_from_prev
    ld_id = await ensure_location_day_from_prev(session, location_id, today)
    
    owners_list = []
    if ld_id:
        q_owners = select(owner).select_from(
            location_day_owners.join(owner, location_day_owners.c.owner_id == owner.c.id)
        ).where(location_day_owners.c.location_day_id == ld_id)
        r_owners = await session.execute(q_owners)
        owners_list = [dict(row._mapping) for row in r_owners.fetchall()]
    
    # Получаем данные за последние 5 дней
    from models.models import location_days, employee_days, employees
    from datetime import timedelta
    
    days_to_load = []
    for i in range(5):
        d = today - timedelta(days=i)
        days_to_load.append(d)
    
    employees_by_day = {}
    for day in days_to_load:
        q_day = select(location_days).where(
            location_days.c.location_id == location_id,
            location_days.c.day == day
        )
        r_day = await session.execute(q_day)
        ld = r_day.fetchone()
        
        if ld:
            # Получаем только работников, которые привязаны к владельцам директора
            # (то есть owner_id должен быть не null и быть в списке владельцев)
            owner_ids = [o['id'] for o in owners_list]
            if owner_ids:
                q_emps = select(employees.c.id, employees.c.name, employee_days.c.owner_id).select_from(
                    employee_days.join(employees, employee_days.c.employee_id == employees.c.id)
                ).where(
                    employee_days.c.day == day,
                    employee_days.c.owner_id.in_(owner_ids)
                )
            else:
                q_emps = select(employees.c.id, employees.c.name, employee_days.c.owner_id).select_from(
                    employee_days.join(employees, employee_days.c.employee_id == employees.c.id)
                ).where(
                    employee_days.c.day == day,
                    employee_days.c.owner_id == None  # Пусто если владельцев нет
                )
            r_emps = await session.execute(q_emps)
            employees_by_day[str(day)] = [dict(row._mapping) for row in r_emps.fetchall()]
        else:
            employees_by_day[str(day)] = []
    
    # Получаем текущую статистику
    q_stats = select(location_day_stats).where(
        location_day_stats.c.location_day_id == ld_id
    )
    r_stats = await session.execute(q_stats)
    stats = r_stats.fetchone()
    
    return {
        "location": dict(loc._mapping) if loc else None,
        "owners": owners_list,
        "employees_by_day": employees_by_day,
        "today": str(today),
        "stats": dict(stats._mapping) if stats else None,
    }
