from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Depends
from auth.auth import superuser_required
from auth.db import User

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get('', response_class=HTMLResponse)
async def admin_panel(request: Request, user: User = Depends(superuser_required)):
    """Admin panel - only superuser can access, HR is explicitly forbidden."""
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Доступ запрещен. Админка доступна только суперпользователям.")
    return templates.TemplateResponse("admin-panel.html", {"request": request, "title": "админка"}) 