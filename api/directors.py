from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Optional, Dict, Any
from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.utils import is_hr

from models.db import get_async_session
from models.models import warehouse_directors, warehouse_directors_history, locations, location_days, location_day_stats, location_day_owners, user
from auth.auth import current_user
from auth.db import User

router = APIRouter(prefix="/directors", tags=["directors"])


async def get_director_locations(session: AsyncSession, user_id: int):
    """Получить все склады, привязанные к директору."""
    q = select(warehouse_directors).where(
        warehouse_directors.c.user_id == user_id,
        warehouse_directors.c.is_active == True
    )
    r = await session.execute(q)
    return r.fetchall()


async def get_director_location(session: AsyncSession, user_id: int, location_id: int = None):
    """Получить конкретную локацию директора. Если location_id не передан - первую."""
    if location_id:
        q = select(warehouse_directors).where(
            warehouse_directors.c.user_id == user_id,
            warehouse_directors.c.location_id == location_id,
            warehouse_directors.c.is_active == True
        )
    else:
        q = select(warehouse_directors).where(
            warehouse_directors.c.user_id == user_id,
            warehouse_directors.c.is_active == True
        ).limit(1)
    r = await session.execute(q)
    wd = r.fetchone()
    return wd


@router.get("/my/locations")
async def get_my_locations(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user_obj=Depends(current_user)
):
    """Получить все склады текущего директора."""
    wd_list = await get_director_locations(session, user_obj.id)
    if not wd_list:
        return {"locations": [], "needs_selection": False}
    
    # Получаем location_id из cookie или используем первый
    location_id = None
    cookie_location_id = request.cookies.get("director_location_id")
    if cookie_location_id:
        try:
            cookie_location_id = int(cookie_location_id)
            for wd in wd_list:
                if wd.location_id == cookie_location_id:
                    location_id = cookie_location_id
                    break
        except (ValueError, TypeError):
            pass
    
    needs_selection = location_id is None
    
    # Получаем информацию о локациях
    location_ids = [wd.location_id for wd in wd_list]
    q = select(locations).where(locations.c.id.in_(location_ids))
    r = await session.execute(q)
    locs = r.fetchall()
    
    return {
        "locations": [dict(loc._mapping) for loc in locs],
        "needs_selection": needs_selection
    }


@router.get("/me")
async def director_me(
    request: Request,
    session: AsyncSession = Depends(get_async_session), 
    user_obj=Depends(current_user)
):
    # Получаем все склады директора
    wd_list = await get_director_locations(session, user_obj.id)
    if not wd_list:
        raise HTTPException(status_code=403, detail="Вы не являетесь директором склада")
    
    # Получаем location_id из cookie или используем первый
    location_id = None
    cookie_location_id = request.cookies.get("director_location_id")
    if cookie_location_id:
        try:
            cookie_location_id = int(cookie_location_id)
            for wd in wd_list:
                if wd.location_id == cookie_location_id:
                    location_id = cookie_location_id
                    break
        except (ValueError, TypeError):
            pass
    
    if location_id is None:
        location_id = wd_list[0].location_id
    
    # Проверяем что выбранный склад привязан
    wd = await get_director_location(session, user_obj.id, location_id)
    if wd is None:
        raise HTTPException(status_code=403, detail="Этот склад не привязан к вашему аккаунту")

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
async def get_director_stats(
    request: Request,
    day: Optional[str] = Query(None), 
    session: AsyncSession = Depends(get_async_session), 
    user_obj: User = Depends(current_user)
):
    """Получить статистику текущего директора за день."""
    # Получаем все склады директора
    wd_list = await get_director_locations(session, user_obj.id)
    if not wd_list:
        raise HTTPException(status_code=403, detail="Вы не являетесь директором склада")
    
    # Получаем location_id из cookie или используем первый
    location_id = None
    cookie_location_id = request.cookies.get("director_location_id")
    if cookie_location_id:
        try:
            cookie_location_id = int(cookie_location_id)
            for wd in wd_list:
                if wd.location_id == cookie_location_id:
                    location_id = cookie_location_id
                    break
        except (ValueError, TypeError):
            pass
    
    if location_id is None:
        location_id = wd_list[0].location_id
    
    # Парсим день (если не указан — сегодня)
    if day:
        try:
            req_day = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты, ожидается YYYY-MM-DD")
    else:
        req_day = datetime.now().date()

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
async def update_stats(
    request: Request,
    day: Optional[str] = Query(None), 
    arrived_actual: Optional[int] = None, 
    expected: Optional[int] = None, 
    outsourcing: Optional[int] = None, 
    overtime: Optional[int] = None, 
    lunch: Optional[int] = None, 
    session: AsyncSession = Depends(get_async_session), 
    user_obj=Depends(current_user)
):
    """Обновить статистику директора. Поддерживает несколько складов через cookie."""
    # Проверка роли: если пользователь директор — он должен быть директором этого склада.
    # HR может редактировать статистику за любые прошедшие дни.
    is_hr_user = await is_hr(session, user_obj.id)
    
    if not is_hr_user:
        # Получаем все склады директора
        wd_list = await get_director_locations(session, user_obj.id)
        if not wd_list:
            raise HTTPException(status_code=403, detail="Вы не являетесь директором склада")
        
        # Получаем location_id из cookie или используем первый
        location_id = None
        cookie_location_id = request.cookies.get("director_location_id")
        if cookie_location_id:
            try:
                cookie_location_id = int(cookie_location_id)
                for wd in wd_list:
                    if wd.location_id == cookie_location_id:
                        location_id = cookie_location_id
                        break
            except (ValueError, TypeError):
                pass
        
        if location_id is None:
            location_id = wd_list[0].location_id
    
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
async def director_dashboard(
    request: Request,
    session: AsyncSession = Depends(get_async_session), 
    user_obj=Depends(current_user)
):
    """Страница для директора склада со статистикой только своего склада.
    Показывает названиие склада, владельцев, работников за последние 5 дней, статистику.
    Поддерживает выбор склада через cookie при нескольких привязанных складах."""
    
    # Проверяем, что пользователь директор
    wd_list = await get_director_locations(session, user_obj.id)
    if not wd_list:
        raise HTTPException(status_code=403, detail="Вы не являетесь директором склада")
    
    # Получаем location_id из cookie или используем первый
    location_id = None
    cookie_location_id = request.cookies.get("director_location_id")
    if cookie_location_id:
        try:
            cookie_location_id = int(cookie_location_id)
            # Проверяем, что этот склад привязан к пользователю
            for wd in wd_list:
                if wd.location_id == cookie_location_id:
                    location_id = cookie_location_id
                    break
        except (ValueError, TypeError):
            pass
    
    # Если не нашли в cookie или нет cookie - берем первый
    if location_id is None:
        location_id = wd_list[0].location_id
    
    # Проверяем что выбранный склад привязан к пользователю
    wd = await get_director_location(session, user_obj.id, location_id)
    if wd is None:
        raise HTTPException(status_code=403, detail="Этот склад не привязан к вашему аккаунту")
    
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
                q_emps = select(
                    employees.c.id, 
                    employees.c.name, 
                    employees.c.terminated_at,
                    employee_days.c.owner_id
                ).select_from(
                    employee_days.join(employees, employee_days.c.employee_id == employees.c.id)
                ).where(
                    employee_days.c.day == day,
                    employee_days.c.owner_id.in_(owner_ids)
                )
            else:
                q_emps = select(
                    employees.c.id, 
                    employees.c.name, 
                    employees.c.terminated_at,
                    employee_days.c.owner_id
                ).select_from(
                    employee_days.join(employees, employee_days.c.employee_id == employees.c.id)
                ).where(
                    employee_days.c.day == day,
                    employee_days.c.owner_id == None  # Пусто если владельцев нет
                )
            r_emps = await session.execute(q_emps)
            emps_list = []
            for row in r_emps.fetchall():
                emp_dict = dict(row._mapping)
                # Проверяем, был ли сотрудник уволнен на эту дату
                terminated_at = emp_dict.get('terminated_at')
                is_fired_today = False
                if terminated_at:
                    from datetime import datetime as _dt
                    terminated_date = terminated_at.date() if isinstance(terminated_at, _dt) else terminated_at
                    if terminated_date == day:
                        is_fired_today = True
                emp_dict['is_fired_today'] = is_fired_today
                emp_dict['terminated_at'] = str(terminated_at) if terminated_at else None
                emps_list.append(emp_dict)
            employees_by_day[str(day)] = emps_list
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


@router.get("/my/locations")
async def get_my_locations(session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    """Получить список всех складов, привязанных к текущему директору."""
    from api.utils import is_hr
    
    # Проверяем что пользователь директор
    wd_list = await get_director_locations(session, user_obj.id)
    if not wd_list:
        # Проверяем, может ли пользователь просматривать директоров (HR/суперюзер)
        is_hr_user = await is_hr(session, user_obj.id)
        is_superuser = getattr(user_obj, 'is_superuser', False)
        if not (is_hr_user or is_superuser):
            raise HTTPException(status_code=403, detail="Вы не являетесь директором склада")
        return {"locations": [], "needs_selection": False}
    
    # Получаем информацию о локациях
    location_ids = [wd.location_id for wd in wd_list]
    q_locs = select(locations).where(locations.c.id.in_(location_ids), locations.c.is_active == True)
    r_locs = await session.execute(q_locs)
    locs = [dict(row._mapping) for row in r_locs.fetchall()]
    
    # Если только один склад - выбор не нужен
    needs_selection = len(locs) > 1
    
    return {
        "locations": locs,
        "needs_selection": needs_selection,
        "count": len(locs)
    }


from fastapi.responses import JSONResponse
from pydantic import BaseModel

class SelectLocationRequest(BaseModel):
    location_id: int

@router.post("/my/select-location")
async def select_location(
    request: Request,
    body: SelectLocationRequest,
    session: AsyncSession = Depends(get_async_session),
    user_obj=Depends(current_user)
):
    """Выбрать текущий склад для работы. Проверяет, что склад привязан к директору. Устанавливает cookie."""
    location_id = body.location_id
    # Проверяем, что пользователь директор
    wd_list = await get_director_locations(session, user_obj.id)
    if not wd_list:
        raise HTTPException(status_code=403, detail="Вы не являетесь директором склада")
    
    # Проверяем, что склад привязан к пользователю
    wd = await get_director_location(session, user_obj.id, location_id)
    if wd is None:
        raise HTTPException(status_code=403, detail="Этот склад не привязан к вашему аккаунту")
    
    # Получаем информацию о локации
    q_loc = select(locations).where(locations.c.id == location_id)
    r_loc = await session.execute(q_loc)
    loc = r_loc.fetchone()
    
    if not loc:
        raise HTTPException(status_code=404, detail="Локация не найдена")
    
    # Создаём ответ с cookie
    response = JSONResponse(content={
        "location_id": location_id,
        "message": f"Выбран склад: {loc.location_name}"
    })
    
    # Устанавливаем cookie на 30 дней
    response.set_cookie(
        key="director_location_id",
        value=str(location_id),
        httponly=True,
        samesite="lax",
        max_age=30 * 24 * 60 * 60  # 30 дней в секундах
    )
    
    return response


@router.get("/my/current-location")
async def get_current_location(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user_obj=Depends(current_user)
):
    """Получить текущий выбранный склад (из cookie или первый доступный)."""
    # Пробуем получить из cookie
    location_id = request.cookies.get("director_location_id")
    
    if location_id:
        try:
            location_id = int(location_id)
            # Проверяем, что склад привязан к пользователю
            wd = await get_director_location(session, user_obj.id, location_id)
            if wd:
                q_loc = select(locations).where(locations.c.id == location_id)
                r_loc = await session.execute(q_loc)
                loc = r_loc.fetchone()
                if loc:
                    return {"location": dict(loc._mapping), "from_cookie": True}
        except (ValueError, TypeError):
            pass
    
    # Если нет в cookie или невалидный - возвращаем первый доступный
    wd_list = await get_director_locations(session, user_obj.id)
    if wd_list:
        # Берем первый или тот что в cookie
        target_location_id = location_id if location_id else wd_list[0].location_id
        
        # Ищем валидную локацию
        for wd in wd_list:
            if wd.location_id == target_location_id:
                q_loc = select(locations).where(locations.c.id == wd.location_id)
                r_loc = await session.execute(q_loc)
                loc = r_loc.fetchone()
                if loc:
                    return {"location": dict(loc._mapping), "from_cookie": False}
        
        # Если не нашли - возвращаем первую
        q_loc = select(locations).where(locations.c.id == wd_list[0].location_id)
        r_loc = await session.execute(q_loc)
        loc = r_loc.fetchone()
        if loc:
            return {"location": dict(loc._mapping), "from_cookie": False}
    
    return {"location": None, "needs_selection": True}


@router.get('/{user_id}/locations')
async def get_director_warehouses(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    user_obj=Depends(current_user)
):
    """Получить все склады, привязанные к директору (для HR)."""
    from api.utils import is_hr
    if not (getattr(user_obj, 'is_superuser', False) or await is_hr(session, user_obj.id)):
        raise HTTPException(status_code=403, detail='Нет доступа')
    
    q = select(
        warehouse_directors.c.id,
        warehouse_directors.c.location_id,
        warehouse_directors.c.user_id,
        warehouse_directors.c.is_active,
        warehouse_directors.c.created_at,
        locations.c.location_name
    ).select_from(
        warehouse_directors.join(locations, warehouse_directors.c.location_id == locations.c.id)
    ).where(
        warehouse_directors.c.user_id == user_id,
        warehouse_directors.c.is_active == True
    )
    r = await session.execute(q)
    items = [dict(row._mapping) for row in r.fetchall()]
    
    return {"locations": items}


@router.post('/{user_id}/locations')
async def add_director_warehouse(
    user_id: int,
    location_id: int,
    session: AsyncSession = Depends(get_async_session),
    user_obj=Depends(current_user)
):
    """Привязать склад к директору (для HR)."""
    from api.utils import is_hr
    if not (getattr(user_obj, 'is_superuser', False) or await is_hr(session, user_obj.id)):
        raise HTTPException(status_code=403, detail='Нет доступа')
    
    # Проверяем что склад существует
    q_loc = select(locations).where(locations.c.id == location_id)
    r_loc = await session.execute(q_loc)
    loc = r_loc.fetchone()
    if not loc:
        raise HTTPException(status_code=404, detail='Склад не найден')
    
    # Проверяем что пользователь существует
    q_user = select(user).where(user.c.id == user_id)
    r_user = await session.execute(q_user)
    usr = r_user.fetchone()
    if not usr:
        raise HTTPException(status_code=404, detail='Пользователь не найден')
    
    # Проверяем, что связь уже не существует (активная)
    q_exists = select(warehouse_directors).where(
        warehouse_directors.c.user_id == user_id,
        warehouse_directors.c.location_id == location_id,
        warehouse_directors.c.is_active == True
    )
    r_exists = await session.execute(q_exists)
    if r_exists.fetchone():
        raise HTTPException(status_code=400, detail='Склад уже привязан к этому директору')
    
    # Деактивируем старую связь если есть
    q_old = select(warehouse_directors).where(
        warehouse_directors.c.user_id == user_id,
        warehouse_directors.c.location_id == location_id,
        warehouse_directors.c.is_active == False
    )
    r_old = await session.execute(q_old)
    old = r_old.fetchone()
    
    if old:
        # Реактивируем старую запись
        await session.execute(
            warehouse_directors.update().where(warehouse_directors.c.id == old.id).values(is_active=True)
        )
    else:
        # Создаём новую запись
        await session.execute(
            warehouse_directors.insert().values(
                user_id=user_id,
                location_id=location_id,
                is_active=True
            )
        )
    
    await session.commit()
    
    return {
        "success": True,
        "message": f"Склад '{loc.location_name}' успешно привязан к директору",
        "location": {"id": location_id, "name": loc.location_name}
    }


@router.delete('/{user_id}/locations/{location_id}')
async def remove_director_warehouse(
    user_id: int,
    location_id: int,
    session: AsyncSession = Depends(get_async_session),
    user_obj=Depends(current_user)
):
    """Отвязать склад от директора (для HR)."""
    from api.utils import is_hr
    if not (getattr(user_obj, 'is_superuser', False) or await is_hr(session, user_obj.id)):
        raise HTTPException(status_code=403, detail='Нет доступа')
    
    # Ищем активную связь
    q = select(warehouse_directors).where(
        warehouse_directors.c.user_id == user_id,
        warehouse_directors.c.location_id == location_id,
        warehouse_directors.c.is_active == True
    )
    r = await session.execute(q)
    wd = r.fetchone()
    
    if not wd:
        raise HTTPException(status_code=404, detail='Связь не найдена')
    
    # Деактивируем связь
    await session.execute(
        warehouse_directors.update().where(warehouse_directors.c.id == wd.id).values(is_active=False)
    )
    await session.commit()
    
    return {"success": True, "message": "Склад успешно отвязан от директора"}
