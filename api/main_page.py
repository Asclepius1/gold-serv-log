from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse


templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="", tags=["Main"])


@router.get('/', response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Главная страница"}) 

@router.get('/contacts', response_class=HTMLResponse)
async def contacts(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request, "title": "Контакты"})
