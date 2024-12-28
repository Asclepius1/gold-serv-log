from typing import Any, Dict, List
from fastapi import Depends, FastAPI, Query, Response, status, Request, HTTPException
from sqlalchemy import select
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse
from api import api_router

from auth.auth import auth_backend, fastapi_users, current_user
from auth.db import User, get_user_db
from auth.schemas import UserCreate, UserRead, UserUpdate
from auth.manager import get_user_manager

from fastapi_users.manager import BaseUserManager
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import get_async_session
app = FastAPI()

@app.exception_handler(StarletteHTTPException)
async def unauthorized_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse(url="/login")
    if exc.status_code == 404:
        return templates.TemplateResponse("404.html", {"request": request})
    if exc.status_code == 403:
        return RedirectResponse(url="/external")
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


# Подключаем папку static для CSS, JS, изображений
app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключаем папку templates для HTML-шаблонов
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173', 'https://localhost:5173', 'https://127.0.0.1:5173'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

