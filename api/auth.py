from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from auth.auth import current_user, superuser_required
from auth.db import User


templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="", tags=["content"])


@router.get('/login', response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "title": "Логин"})

@router.get('/internal', response_class=HTMLResponse)
async def internal(request: Request, user: User = Depends(superuser_required)):
    return templates.TemplateResponse("internal.html", {"request": request, "title": "ВНУ"}) 

@router.get('/external', response_class=HTMLResponse)
async def external(request: Request, user: User = Depends(current_user)):
    return templates.TemplateResponse("external.html", {"request": request, "title": "ВНЕ"}) 