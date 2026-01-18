from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from auth.auth import current_user, superuser_required
from auth.db import User
from models.db import get_async_session
from models.models import warehouse_directors
from models.models import hrs
from sqlalchemy import select
from api.utils import is_hr


templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="", tags=["content"])


# ==================== Зависимости для проверки ролей ====================

async def director_required(user: User = Depends(current_user), session: AsyncSession = Depends(get_async_session)) -> User:
    """Проверка: пользователь должен быть директором склада."""
    q = select(warehouse_directors).where(
        warehouse_directors.c.user_id == user.id,
        warehouse_directors.c.is_active == True
    )
    r = await session.execute(q)
    director = r.fetchone()
    
    if not director:
        raise HTTPException(status_code=403, detail="Доступ запрещен. Требуется роль директора.")
    
    return user


async def admin_required(user: User = Depends(current_user), session: AsyncSession = Depends(get_async_session)) -> User:
    """Проверка: пользователь должен быть суперпользователем (только админ)."""
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Доступ запрещен. Требуется роль администратора.")
    
    return user


async def hr_required(user: User = Depends(current_user), session: AsyncSession = Depends(get_async_session)) -> User:
    """Проверка: пользователь должен быть HR или суперпользователем."""
    # Суперпользователь (админ) может заходить на HR страницу
    if user.is_superuser:
        return user
    
    is_hr_user = await is_hr(session, user.id)
    if not is_hr_user:
        raise HTTPException(status_code=403, detail="Доступ запрещен. Требуется роль HR.")
    
    return user


# ==================== Маршруты ====================


@router.get('/login', response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "title": "Логин"})

@router.get('/internal', response_class=HTMLResponse)
async def internal(request: Request, user: User = Depends(admin_required)):
    return templates.TemplateResponse("internal.html", {"request": request, "title": "ВНУ"})

@router.get('/hr', response_class=HTMLResponse)
async def hr_page(request: Request, user: User = Depends(hr_required)):
    return templates.TemplateResponse("hr.html", {"request": request, "title": "HR — Панель управления", "is_admin": user.is_superuser})

@router.get('/external', response_class=HTMLResponse)
async def external(request: Request, user: User = Depends(current_user)):
    return templates.TemplateResponse("external.html", {"request": request, "title": "ВНЕ"})


@router.get('/dashboard')
async def dashboard(request: Request, user: User = Depends(current_user), session: AsyncSession = Depends(get_async_session)):
    """Маршрут для перенаправления на нужную страницу в зависимости от роли пользователя."""
    
    # Сначала проверяем, является ли пользователь администратором (superuser)
    if user.is_superuser:
        return RedirectResponse(url="/internal", status_code=302)
    
    # Проверяем, является ли пользователь HR
    is_hr_user = await is_hr(session, user.id)
    if is_hr_user:
        return RedirectResponse(url="/hr", status_code=302)
    
    # Потом проверяем, является ли пользователь директором
    q = select(warehouse_directors).where(
        warehouse_directors.c.user_id == user.id,
        warehouse_directors.c.is_active == True
    )
    r = await session.execute(q)
    director = r.fetchone()
    
    if director:
        # Это директор склада - перенаправляем на его панель
        return RedirectResponse(url="/director", status_code=302)
    
    # По умолчанию перенаправляем на внешнюю страницу
    return RedirectResponse(url="/external", status_code=302)
    
    if director:
        # Это директор склада - перенаправляем на его панель
        return RedirectResponse(url="/director", status_code=302)
    
    # По умолчанию перенаправляем на внешнюю страницу
    return RedirectResponse(url="/external", status_code=302)


@router.get('/logout')
async def logout(request: Request):
    """Логаут пользователя и перенаправление на страницу входа."""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("fastapiusersauth")
    return response