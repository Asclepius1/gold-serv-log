from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Optional
from sqlalchemy import select, insert, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import get_async_session
from models.models import employees, employee_days, owner, location_days, location_day_owners
from models.schemas import EmployeeAssignmentUpdate
from auth.auth import current_user
from api.utils import is_hr

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("/{employee_id}/history")
async def get_employee_history(employee_id: int, session: AsyncSession = Depends(get_async_session), user=Depends(current_user)):
    """Получить историю привязок работника к владельцам за последние 30 дней"""
    
    # Доступ: superuser или HR
    if not (getattr(user, 'is_superuser', False) or await is_hr(session, user.id)):
        raise HTTPException(status_code=403, detail="Нет доступа к истории")
    
    # Проверим существование сотрудника
    q_emp = select(employees).where(employees.c.id == employee_id)
    res_emp = await session.execute(q_emp)
    emp = res_emp.fetchone()
    if emp is None:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    
    # Получаем историю за последние 30 дней
    today = datetime.now().date()
    start_date = today - timedelta(days=30)
    
    q_history = select(employee_days).where(
        employee_days.c.employee_id == employee_id,
        employee_days.c.day >= start_date,
        employee_days.c.day <= today
    ).order_by(employee_days.c.day.desc())
    
    res_history = await session.execute(q_history)
    history = []
    
    for row in res_history.fetchall():
        ed = dict(row._mapping)
        
        # Получаем имя владельца если есть
        owner_name = None
        if ed['owner_id']:
            q_owner = select(owner).where(owner.c.id == ed['owner_id'])
            r_owner = await session.execute(q_owner)
            o = r_owner.fetchone()
            owner_name = o.name if o else None
        
        history.append({
            "day": str(ed['day']),
            "owner_id": ed['owner_id'],
            "owner_name": owner_name,
            "finalized": ed.get('finalized', False)
        })
    
    return {"employee_id": employee_id, "employee_name": emp.name, "history": history}


@router.get("/{employee_id}/assignment")
async def get_employee_assignment(employee_id: int, day: Optional[str] = Query(None), session: AsyncSession = Depends(get_async_session), user=Depends(current_user)):
    if day:
        try:
            req_day = datetime.strptime(day, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="Неверный формат даты, ожидается YYYY-MM-DD")
    else:
        req_day = datetime.now().date()

    # Доступ: superuser или HR
    if not (getattr(user, 'is_superuser', False) or await is_hr(session, user.id)):
        raise HTTPException(status_code=403, detail="Нет доступа к данным сотрудника")

    # Найдем запись дня для сотрудника
    q = select(employee_days).where(employee_days.c.employee_id == employee_id, employee_days.c.day == req_day)
    res = await session.execute(q)
    ed = res.fetchone()

    if ed is None:
        # Попробуем найти последнюю запись до req_day
        q2 = select(employee_days).where(employee_days.c.employee_id == employee_id, employee_days.c.day < req_day).order_by(employee_days.c.day.desc()).limit(1)
        res2 = await session.execute(q2)
        prev = res2.fetchone()
        if prev is None:
            return {"day": str(req_day), "owner": None}

        # Дублируем предыдущий день
        ins = employee_days.insert().values(employee_id=employee_id, day=req_day, owner_id=prev.owner_id, finalized=False).returning(employee_days.c.id)
        result = await session.execute(ins)
        new_id = result.scalar_one()
        await session.commit()

        if prev.owner_id is None:
            return {"day": str(req_day), "owner": None}

        q3 = select(owner.c.id, owner.c.name).where(owner.c.id == prev.owner_id)
        res3 = await session.execute(q3)
        o = res3.fetchone()
        return {"day": str(req_day), "owner": dict(o._mapping) if o else None}

    # Если запись существует — вернуть owner
    if ed.owner_id is None:
        return {"day": str(req_day), "owner": None}
    q4 = select(owner.c.id, owner.c.name).where(owner.c.id == ed.owner_id)
    res4 = await session.execute(q4)
    o2 = res4.fetchone()
    return {"day": str(req_day), "owner": dict(o2._mapping) if o2 else None}


@router.post("/{employee_id}/assignment")
async def set_employee_assignment(employee_id: int, data: EmployeeAssignmentUpdate, day: Optional[str] = Query(None), session: AsyncSession = Depends(get_async_session), user=Depends(current_user)):
    owner_id = data.owner_id
    # Доступ: superuser или HR
    if not (getattr(user, 'is_superuser', False) or await is_hr(session, user.id)):
        raise HTTPException(status_code=403, detail="Нет доступа к изменению сотрудника")

    # Проверим существование сотрудника и статус
    q_emp = select(employees).where(employees.c.id == employee_id)
    res_emp = await session.execute(q_emp)
    emp = res_emp.fetchone()
    if emp is None:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    if not emp.is_active:
        raise HTTPException(status_code=400, detail="Сотрудник уволен — изменения недоступны")
    if emp.terminated_at is not None:
        term_date = emp.terminated_at.date()

    if day:
        try:
            req_day = datetime.strptime(day, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="Неверный формат даты, ожидается YYYY-MM-DD")
    else:
        req_day = datetime.now().date()

    today = datetime.now().date()
    
    # Проверка прав на изменение прошлых дней
    # Только суперпользователь (админ) может менять прошедшие дни
    if req_day < today and not getattr(user, 'is_superuser', False):
        raise HTTPException(status_code=400, detail="Только администратор может менять назначение для прошлых дней")

    if emp.terminated_at is not None and req_day >= emp.terminated_at.date():
        raise HTTPException(status_code=400, detail="Нельзя назначать владельца после даты увольнения")

    # Найдем или создадим запись дня
    q = select(employee_days).where(employee_days.c.employee_id == employee_id, employee_days.c.day == req_day)
    res = await session.execute(q)
    ed = res.fetchone()

    if ed is None:
        ins = employee_days.insert().values(employee_id=employee_id, day=req_day, owner_id=owner_id, finalized=False)
        await session.execute(ins)
    else:
        if ed.finalized:
            raise HTTPException(status_code=400, detail="День зафиксирован и не может быть изменён")
        await session.execute(employee_days.update().where(employee_days.c.id == ed.id).values(owner_id=owner_id))

    await session.commit()
    return {"day": str(req_day), "owner_set": owner_id}


@router.post("/{employee_id}/terminate")
async def terminate_employee(employee_id: int, terminate_at: Optional[str] = Query(None), session: AsyncSession = Depends(get_async_session), user=Depends(current_user)):
    # terminate_at optional YYYY-MM-DD, default today
    if terminate_at:
        try:
            t_date = datetime.strptime(terminate_at, "%Y-%m-%d")
        except Exception:
            raise HTTPException(status_code=400, detail="Неверный формат даты, ожидается YYYY-MM-DD")
    else:
        t_date = datetime.now()

    # Доступ: superuser или HR
    if not (getattr(user, 'is_superuser', False) or await is_hr(session, user.id)):
        raise HTTPException(status_code=403, detail="Нет доступа для увольнения сотрудника")

    q_emp = select(employees).where(employees.c.id == employee_id)
    res_emp = await session.execute(q_emp)
    emp = res_emp.fetchone()
    if emp is None:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    # При увольнении: устанавливаем дату увольнения и очищаем дату возвращения
    await session.execute(employees.update().where(employees.c.id == employee_id).values(
        is_active=False, 
        terminated_at=t_date,
        rehired_at=None
    ))
    await session.commit()
    return {"employee_id": employee_id, "terminated_at": t_date.isoformat()}


@router.get('/list')
async def list_employees(day: Optional[str] = Query(None), location_id: Optional[int] = Query(None), session: AsyncSession = Depends(get_async_session), user=Depends(current_user)):
    # доступ: superuser или HR
    from api.utils import is_hr
    if not (getattr(user, 'is_superuser', False) or await is_hr(session, user.id)):
        raise HTTPException(status_code=403, detail='Нет доступа')
    
    # Определяем дату для проверки активности сотрудников
    d = None
    if day:
        try:
            from datetime import datetime as _dt
            d = _dt.strptime(day, '%Y-%m-%d').date()
        except Exception:
            d = None
    else:
        from datetime import datetime as _dt
        d = _dt.now().date()
    
    # Получаем только активных сотрудников на эту дату
    # Сотрудник активен, если:
    # 1. is_active = True И
    # 2. (terminated_at = NULL ИЛИ terminated_at > дата)
    q = select(employees.c.id, employees.c.name, employees.c.terminated_at).where(
        employees.c.is_active == True
    )
    r = await session.execute(q)
    
    # Фильтруем по дате увольнения на клиенте
    emps = []
    for row in r.fetchall():
        row_dict = dict(row._mapping)
        terminated_at = row_dict.get('terminated_at')
        
        # Если сотрудник был уволен ДО этой даты, пропускаем его
        if terminated_at:
            from datetime import datetime as _dt
            terminated_date = terminated_at.date() if isinstance(terminated_at, _dt) else terminated_at
            if d and terminated_date <= d:
                # Сотрудник был уволен ДО или В эту дату, значит он не активен
                continue
        
        emps.append({"id": row_dict['id'], "name": row_dict['name']})

    results = []
    for e in emps:
        owner_id = None
        owner_name = None
        if d:
            q2 = select(employee_days.c.owner_id).where(employee_days.c.employee_id == e['id'], employee_days.c.day == d)
            r2 = await session.execute(q2)
            row = r2.fetchone()
            if row:
                owner_id = row.owner_id
                if owner_id:
                    q3 = select(owner.c.name).where(owner.c.id == owner_id)
                    r3 = await session.execute(q3)
                    o = r3.fetchone()
                    owner_name = o.name if o else None
            else:
                # If no record for today, try to get from previous day
                prev_day = d - timedelta(days=1)
                q_prev = select(employee_days.c.owner_id).where(employee_days.c.employee_id == e['id'], employee_days.c.day == prev_day)
                r_prev = await session.execute(q_prev)
                prev_row = r_prev.fetchone()
                if prev_row and prev_row.owner_id:
                    owner_id = prev_row.owner_id
                    q3 = select(owner.c.name).where(owner.c.id == owner_id)
                    r3 = await session.execute(q3)
                    o = r3.fetchone()
                    owner_name = o.name if o else None
        results.append({"id": e['id'], "name": e['name'], "owner_id": owner_id, "owner_name": owner_name})

    # NOTE: We show ALL active employees regardless of location_id.
    # location_id parameter is used for context but does not filter results.
    # This allows viewing all employees and assigning them to owners for a specific location.

    return {"employees": results}


@router.post("/init-day/{day}")
async def init_employee_day(day: str, session: AsyncSession = Depends(get_async_session), user=Depends(current_user)):
    """Инициализирует данные работников на заданный день на основе предыдущего дня.
    Если для работника нет записи на этот день, копируется привязка с предыдущего дня.
    Не копирует данные для сотрудников, которые были уволены ДО целевого дня.
    Удаляет привязку сотрудника если он был уволен ДО целевого дня (но не в день увольнения)."""
    
    # Доступ: superuser или HR
    if not (getattr(user, 'is_superuser', False) or await is_hr(session, user.id)):
        raise HTTPException(status_code=403, detail="Нет доступа")
    
    try:
        target_day = datetime.strptime(day, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(status_code=400, detail="Неверный формат даты, ожидается YYYY-MM-DD")
    
    prev_day = target_day - timedelta(days=1)
    
    # Получаем всех активных работников, которые НЕ уволены на целевой день
    q_emps = select(employees).where(employees.c.is_active == True)
    res_emps = await session.execute(q_emps)
    
    count_copied = 0
    count_removed = 0
    
    for emp_row in res_emps.fetchall():
        emp_id = emp_row.id
        
        # Пропускаем, если сотрудник был уволен ДО целевой дня
        if emp_row.terminated_at:
            terminated_date = emp_row.terminated_at.date() if isinstance(emp_row.terminated_at, datetime) else emp_row.terminated_at
            if terminated_date < target_day:
                # Сотрудник был уволен раньше целевого дня
                # Удаляем его привязку если есть
                await session.execute(
                    delete(employee_days).where(
                        employee_days.c.employee_id == emp_id,
                        employee_days.c.day == target_day
                    )
                )
                count_removed += 1
                continue
            elif terminated_date == target_day:
                # Сотрудник уволен ВО целевой день
                # Проверяем есть ли привязка на день увольнения
                q_check = select(employee_days).where(
                    employee_days.c.employee_id == emp_id,
                    employee_days.c.day == target_day
                )
                res_check = await session.execute(q_check)
                if res_check.fetchone() is None:
                    # Если нет привязки, копируем с предыдущего дня
                    q_prev = select(employee_days).where(
                        employee_days.c.employee_id == emp_id,
                        employee_days.c.day == prev_day
                    )
                    res_prev = await session.execute(q_prev)
                    prev_ed = res_prev.fetchone()
                    if prev_ed:
                        ins = employee_days.insert().values(
                            employee_id=emp_id,
                            day=target_day,
                            owner_id=prev_ed.owner_id,
                            finalized=False
                        )
                        await session.execute(ins)
                continue
        
        # Проверяем, есть ли запись на целевой день
        q_target = select(employee_days).where(
            employee_days.c.employee_id == emp_id,
            employee_days.c.day == target_day
        )
        res_target = await session.execute(q_target)
        
        if res_target.fetchone() is None:
            # Ищем запись на предыдущий день
            q_prev = select(employee_days).where(
                employee_days.c.employee_id == emp_id,
                employee_days.c.day == prev_day
            )
            res_prev = await session.execute(q_prev)
            prev_ed = res_prev.fetchone()
            
            if prev_ed:
                # Копируем привязку с предыдущего дня
                ins = employee_days.insert().values(
                    employee_id=emp_id,
                    day=target_day,
                    owner_id=prev_ed.owner_id,
                    finalized=False
                )
                await session.execute(ins)
                count_copied += 1
    
    await session.commit()
    return {"day": str(target_day), "records_copied": count_copied, "records_removed": count_removed}