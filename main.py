import pytz

from datetime import datetime
from config import HOST
from api import api_router
from api.logs import run_add_logs

from sqlalchemy import select

from starlette.exceptions import HTTPException as StarletteHTTPException

from fastapi import Depends, FastAPI, Query, Response, status, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse
from apscheduler.schedulers.background import BackgroundScheduler

from auth.auth import auth_backend, fastapi_users, current_user
from auth.schemas import UserCreate, UserRead, UserUpdate

from contextlib import asynccontextmanager

timezone_almaty = pytz.timezone('Asia/Almaty')

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()

    scheduler.add_job(run_add_logs, 'cron', hour=7, minute=0, timezone=timezone_almaty)
    scheduler.add_job(run_add_logs, 'cron', hour=13, minute=20, timezone=timezone_almaty)
    scheduler.add_job(run_add_logs, 'cron', hour=18, minute=20, timezone=timezone_almaty)

    scheduler.start()
    print("Планировщик запущен")
    
    yield  # Даем FastAPI стартовать

    scheduler.shutdown()
    print("Планировщик остановлен")

app = FastAPI(lifespan=lifespan)

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
    allow_origins=['http://localhost:8000', 
                   'http://127.0.0.1:8000', 
                   'http://194.32.140.25:8000', 
                   'http://194.32.140.25',
                   'https://194.32.140.25'],
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, reload=True)
    