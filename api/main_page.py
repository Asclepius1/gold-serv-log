from fastapi import APIRouter, Depends, FastAPI, Response, status, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles


templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="", tags=["Main"])


@router.get('/', response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Главная страница"}) 

@router.get('/contacts', response_class=HTMLResponse)
async def contacts(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request, "title": "Контакты"})
