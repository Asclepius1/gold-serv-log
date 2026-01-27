from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
import secrets
import bcrypt

from models.db import get_async_session
from models.models import employees, locations, warehouse_directors, warehouse_directors_history, user
from datetime import date
from api.utils import is_hr
from auth.auth import current_user

router = APIRouter(prefix="/hr_admin", tags=["hr_admin"])


async def assert_superuser_only(user_obj):
    """Проверка: пользователь должен быть суперпользователем. HR не может использовать эти endpoints."""
    if not getattr(user_obj, 'is_superuser', False):
        raise HTTPException(status_code=403, detail="Нет доступа. Эти функции доступны только для администраторов.")


@router.get('/employees')
async def list_employees_admin(show_inactive: bool = False, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    assert_superuser_only(user_obj)
    if show_inactive:
        q = select(employees.c.id, employees.c.name, employees.c.is_active, employees.c.terminated_at).where(employees.c.is_active == False)
    else:
        q = select(employees.c.id, employees.c.name, employees.c.is_active, employees.c.terminated_at).where(employees.c.is_active == True)
    r = await session.execute(q)
    items = [dict(row._mapping) for row in r.fetchall()]
    return {"employees": items}


@router.post('/employees')
async def create_employee_admin(name: str, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    assert_superuser_only(user_obj)
    ins = insert(employees).values(name=name, is_active=True)
    res = await session.execute(ins)
    await session.commit()
    return {"created": name}


@router.put('/employees/{employee_id}')
async def update_employee_admin(employee_id: int, name: Optional[str] = None, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    assert_superuser_only(user_obj)
    if name is None:
        raise HTTPException(status_code=400, detail="No fields to update")
    await session.execute(update(employees).where(employees.c.id == employee_id).values(name=name))
    await session.commit()
    return {"updated": employee_id}


@router.post('/employees/{employee_id}/fire')
async def fire_employee_admin(employee_id: int, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    assert_superuser_only(user_obj)
    from datetime import datetime
    # Устанавливаем дату увольнения сегодня, если уволен раньше то обновляем дату
    await session.execute(update(employees).where(employees.c.id == employee_id).values(
        is_active=False, 
        terminated_at=datetime.utcnow(),
        rehired_at=None  # Очищаем дату возвращения при новом увольнении
    ))
    await session.commit()
    return {"fired": employee_id}


@router.post('/employees/{employee_id}/reactivate')
async def reactivate_employee_admin(employee_id: int, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    assert_superuser_only(user_obj)
    from datetime import datetime
    # При возврате устанавливаем дату возвращения и очищаем дату увольнения
    await session.execute(update(employees).where(employees.c.id == employee_id).values(
        is_active=True, 
        terminated_at=None,
        rehired_at=datetime.utcnow()
    ))
    await session.commit()
    return {"reactivated": employee_id}


@router.get('/locations')
async def list_locations_admin(show_inactive: bool = False, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    assert_superuser_only(user_obj)
    if show_inactive:
        q = select(locations.c.id, locations.c.location_name, locations.c.is_active).where(locations.c.is_active == False)
    else:
        q = select(locations.c.id, locations.c.location_name, locations.c.is_active).where(locations.c.is_active == True)
    r = await session.execute(q)
    items = [dict(row._mapping) for row in r.fetchall()]
    return {"locations": items}


@router.post('/locations')
async def create_location_admin(location_name: str, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    assert_superuser_only(user_obj)
    await session.execute(insert(locations).values(location_name=location_name, is_active=True))
    await session.commit()
    return {"created": location_name}


@router.put('/locations/{location_id}')
async def update_location_admin(location_id: int, location_name: str, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    assert_superuser_only(user_obj)
    await session.execute(update(locations).where(locations.c.id == location_id).values(location_name=location_name))
    await session.commit()
    return {"updated": location_id}


@router.delete('/locations/{location_id}')
async def delete_location_admin(location_id: int, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    assert_superuser_only(user_obj)
    await session.execute(update(locations).where(locations.c.id == location_id).values(is_active=False))
    await session.commit()
    return {"deactivated": location_id}


@router.post('/locations/{location_id}/reactivate')
async def reactivate_location_admin(location_id: int, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    assert_superuser_only(user_obj)
    await session.execute(update(locations).where(locations.c.id == location_id).values(is_active=True))
    await session.commit()
    return {"reactivated": location_id}


@router.get('/directors')
async def list_directors_admin(show_inactive: bool = False, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    assert_superuser_only(user_obj)
    # Return directors with user name joined
    if show_inactive:
        q = select(warehouse_directors.c.user_id, warehouse_directors.c.location_id, warehouse_directors.c.is_active, user.c.name, user.c.email).select_from(
            warehouse_directors.join(user, warehouse_directors.c.user_id == user.c.id)
        ).where(warehouse_directors.c.is_active == False)
    else:
        q = select(warehouse_directors.c.user_id, warehouse_directors.c.location_id, warehouse_directors.c.is_active, user.c.name, user.c.email).select_from(
            warehouse_directors.join(user, warehouse_directors.c.user_id == user.c.id)
        ).where(warehouse_directors.c.is_active == True)
    r = await session.execute(q)
    items = [dict(row._mapping) for row in r.fetchall()]
    return {"directors": items}


@router.post('/directors')
async def create_director_admin(user_id: int, location_id: int, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    assert_superuser_only(user_obj)
    # Проверим что пользователь существует
    q = select(user).where(user.c.id == user_id)
    r = await session.execute(q)
    if r.fetchone() is None:
        raise HTTPException(status_code=404, detail="User not found")
    await session.execute(insert(warehouse_directors).values(user_id=user_id, location_id=location_id, is_active=True))
    # Record in history with today's date
    today = date.today()
    await session.execute(insert(warehouse_directors_history).values(user_id=user_id, location_id=location_id, day=today))
    await session.commit()
    return {"created": {"user_id": user_id, "location_id": location_id}}


@router.post('/directors/create_user')
async def create_director_with_user(name: str, location_id: int, email: Optional[str] = None, password: Optional[str] = None, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    """Create a new user account (login/password) and assign as warehouse director for location.
    Returns plain credentials so admin can pass them to the director.
    """
    
    # require email and password (they act as login credentials)
    if not email or not str(email).strip():
        raise HTTPException(status_code=400, detail="Email is required")
    email = str(email).strip().lower()
    if not password or not str(password).strip():
        raise HTTPException(status_code=400, detail="Password is required")
    password = str(password)

    # check uniqueness of email
    q_check = select(user.c.id).where(user.c.email == email)
    rr = await session.execute(q_check)
    if rr.fetchone() is not None:
        raise HTTPException(status_code=400, detail="Email already in use")

    # hash password with bcrypt
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Use RETURNING to reliably obtain new user id with async drivers
    ins = insert(user).values(name=name, email=email, hashed_password=hashed, is_active=True, is_superuser=False, is_verified=False).returning(user.c.id)
    result = await session.execute(ins)
    try:
        new_id = result.scalar_one()
    except Exception:
        # fallback: try to select by email
        q = select(user.c.id).where(user.c.email == email).order_by(user.c.id.desc()).limit(1)
        rr = await session.execute(q)
        row = rr.fetchone()
        new_id = row._mapping['id'] if row is not None else None
    if not new_id:
        raise HTTPException(status_code=500, detail="Failed to create user")

    await session.execute(insert(warehouse_directors).values(user_id=new_id, location_id=location_id, is_active=True))
    # Record in history with today's date
    today = date.today()
    await session.execute(insert(warehouse_directors_history).values(user_id=new_id, location_id=location_id, day=today))
    await session.commit()
    return {"created": {"user_id": new_id, "name": name, "location_id": location_id}, "credentials": {"login": email, "password": password}}


@router.put('/directors/{user_id}/name')
async def update_director_name(user_id: int, name: str, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    assert_superuser_only(user_obj)
    await session.execute(update(user).where(user.c.id == user_id).values(name=name))
    await session.commit()
    return {"updated": {"user_id": user_id, "name": name}}


@router.put('/directors/{user_id}')
async def update_director_admin(user_id: int, location_id: int, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    assert_superuser_only(user_obj)
    await session.execute(update(warehouse_directors).where(warehouse_directors.c.user_id == user_id).values(location_id=location_id))
    # Record change in history with today's date
    today = date.today()
    await session.execute(insert(warehouse_directors_history).values(user_id=user_id, location_id=location_id, day=today))
    await session.commit()
    return {"updated": user_id}


@router.delete('/directors/{user_id}')
async def delete_director_admin(user_id: int, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    assert_superuser_only(user_obj)
    # deactivate director mapping
    await session.execute(update(warehouse_directors).where(warehouse_directors.c.user_id == user_id).values(is_active=False))
    # also deactivate user account
    await session.execute(update(user).where(user.c.id == user_id).values(is_active=False))
    await session.commit()
    return {"deactivated": user_id}


@router.post('/directors/{user_id}/reactivate')
async def reactivate_director_admin(user_id: int, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    assert_superuser_only(user_obj)
    # reactivate mapping and user account
    await session.execute(update(warehouse_directors).where(warehouse_directors.c.user_id == user_id).values(is_active=True))
    await session.execute(update(user).where(user.c.id == user_id).values(is_active=True))
    await session.commit()
    return {"reactivated": user_id}


@router.put('/directors/{user_id}/credentials')
async def update_director_credentials(user_id: int, email: Optional[str] = None, password: Optional[str] = None, name: Optional[str] = None, session: AsyncSession = Depends(get_async_session), user_obj=Depends(current_user)):
    assert_superuser_only(user_obj)
    values = {}
    if email is not None:
        email = str(email).strip().lower()
        # check uniqueness excluding current user
        qchk = select(user.c.id).where(user.c.email == email).where(user.c.id != user_id)
        rchk = await session.execute(qchk)
        if rchk.fetchone() is not None:
            raise HTTPException(status_code=400, detail="Email already in use")
        values['email'] = email
    if name is not None:
        values['name'] = name
    if password is not None:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        values['hashed_password'] = hashed
    if not values:
        raise HTTPException(status_code=400, detail="No fields to update")
    await session.execute(update(user).where(user.c.id == user_id).values(**values))
    await session.commit()
    return {"updated": {"user_id": user_id}}
