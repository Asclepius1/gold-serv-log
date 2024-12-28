from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi import Depends, HTTPException
from typing import List
from auth.auth import current_user, superuser_required
from auth.db import User

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get('', response_class=HTMLResponse)
async def internal(request: Request, user: User = Depends(superuser_required)):
    return templates.TemplateResponse("admin-panel.html", {"request": request, "title": "админка"}) 