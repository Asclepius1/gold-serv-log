from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import get_async_session
from api.utils import is_hr
from auth.auth import current_user
from auth.db import User


templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="", tags=["Main"])


@router.get('/', response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Главная страница"}) 

@router.get('/contacts', response_class=HTMLResponse)
async def contacts(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request, "title": "Контакты"})


@router.get('/hr', response_class=HTMLResponse)
async def hr_page(request: Request, session: AsyncSession = Depends(get_async_session), user: User = Depends(current_user)):
    # Проверим, что пользователь — HR или суперпользователь
    is_superuser = getattr(user, 'is_superuser', False)
    if not (is_superuser or await is_hr(session, user.id)):
        return templates.TemplateResponse("404.html", {"request": request, "title": "Нет доступа"}, status_code=403)
    return templates.TemplateResponse("hr.html", {"request": request, "title": "HR панель"})


@router.get('/director', response_class=HTMLResponse)
async def director_page(request: Request, session: AsyncSession = Depends(get_async_session), user: User = Depends(current_user)):
    # Проверим, что пользователь — директор склада
    from models.models import warehouse_directors
    from sqlalchemy import select
    
    q = select(warehouse_directors).where(
        warehouse_directors.c.user_id == user.id,
        warehouse_directors.c.is_active == True
    )
    r = await session.execute(q)
    director = r.fetchone()
    
    if director is None:
        raise HTTPException(status_code=403, detail="Доступ запрещен. Требуется роль директора.")
    
    return templates.TemplateResponse("director_dashboard.html", {"request": request, "title": "Директор склада"})
