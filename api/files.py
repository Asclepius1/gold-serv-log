import asyncio
import os
import time as time_
import random
from typing import List
from pathlib import Path
from datetime import datetime, time, timedelta

from fastapi.responses import FileResponse
import requests
from config import BEARER_TOKEN_GOLD_SERV, GOLD_SERV_API_URL
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile

from sqlalchemy.future import select
from sqlalchemy import Text, cast, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import files, owner as owner_db
from models.db import get_async_session, redis_client
from auth.auth import superuser_required, current_user
from auth.db import User
from schedule import update_scheduler

router = APIRouter(prefix="/files", tags=["files"], )

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

def get_files_by_owner(owner: str) -> Path|None:

    url = f"{GOLD_SERV_API_URL}/?depositor={owner}"
    headers = {'Authorization': f'Bearer {BEARER_TOKEN_GOLD_SERV}'}
    response = requests.get(url, headers=headers, verify=False)

    if response.status_code == 200:
        owner_dir = UPLOAD_DIR / owner 
        owner_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now().strftime("%d%m%Y_%H%M%S")
        rand = "".join([str(random.randint(0, 9)) for _ in range(8)]) 

        file_path = owner_dir / f"{owner}_{now}_({rand}).xlsx"

        with open(file_path, "wb") as f:
            f.write(response.content)

        print(f"Файл сохранен как {file_path}.xlsx")
        return file_path
    else:
        print(f"Ошибка: {response.status_code}")


@router.post("/upload/")
async def upload_file(owner_id: int, session: AsyncSession = Depends(get_async_session), user: User = Depends(current_user)):
    
    owner_result = await session.execute(owner_db.select().where(owner_db.c.id == owner_id))
    result = owner_result.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Владелец не найден")
    
    file_path = get_files_by_owner(result.name)

    if not file_path:
        raise HTTPException(status_code=404, detail="Файл не найден")

    query = files.insert().values(
        owner_id=owner_id,
        filename=file_path.name,
        file_path=str(file_path)
    )
    await session.execute(query)
    await session.commit()

    return {"message": f"Файл {file_path.name} добавлен в БД"}




@router.get("/download/{file_id}")
async def download_file(file_id: int, session: AsyncSession = Depends(get_async_session), user: User = Depends(current_user)):
    result = await session.execute(files.select().where(files.c.id == file_id))
    file = result.fetchone()
    if file:
        file_path = Path(file.file_path)
        if file_path.exists():
            return FileResponse(file_path, filename=file.filename)
    raise HTTPException(status_code=404, detail="Файл не найден")

async def delete_old_files():
    async for session in get_async_session():
        threshold_date = datetime.now() - timedelta(days=30)
        print(threshold_date)
        # Получаем только `file_path` и `id`, чтобы не загружать лишние данные
        result = await session.execute(select(files.c.id, files.c.file_path).where(files.c.created_at < threshold_date))
        old_files = result.all()

        if not old_files:
            print("нет старых файлов")
            return  # Если старых файлов нет, ничего не делаем

        # Удаляем файлы из системы
        for file_id, file_path in old_files:
            file_path = Path(file_path)
            if file_path.exists():
                os.remove(file_path)
        print("файлы были удалены")
        # Удаляем файлы из базы за 1 SQL-запрос (оптимизировано)
        await session.execute(files.delete().where(files.c.id.in_([file_id for file_id, _ in old_files])))
        await session.commit()

@router.get("/{owner_id}")
async def get_file_path_by_owner_id(owner_id: int, session: AsyncSession = Depends(get_async_session), user: User = Depends(current_user)):
    result = await session.execute(files.select().where(files.c.owner_id == owner_id).order_by(files.c.created_at.desc()))
    files_data = result.scalars()
    if files_data:
        return [
            {
                "id": item.id,
                "name": item.filename,
                "date": item.created_at,
                "type": "file"
            }
            for item in result
        ]
    raise HTTPException(status_code=404, detail="Файл не найден")


BUTTON_KEY = "button_press"

def get_button_status(button_id: str):
    current_time = int(time_.time())
    button_key = f"button_press:{button_id}"

    # Получаем данные по конкретной кнопке
    press_data = redis_client.hgetall(button_key)

    if not press_data:
        redis_client.hset(button_key, mapping={"count": 0, "last_press": 0})

    press_count = int(press_data.get("count", 0))
    last_press_time = int(press_data.get("last_press", 0))

    # Если прошло 24 часа с первого нажатия, сбрасываем счетчик
    if press_count >= 2 and (current_time - last_press_time) >= 43200:
        redis_client.hset(button_key, mapping={"count": 0, "last_press": 0})
        press_count = 0
        last_press_time = 0

    return {
        "button_id": button_id,
        "attempts_left": max(0, 2 - press_count),
        "last_press_time": last_press_time
    }

@router.get("/button_status/{button_id}")
def button_status(button_id: str, user: User = Depends(current_user)):
    return get_button_status(button_id)

@router.post("/press_button/{button_id}")
def press_button(button_id: str, user: User = Depends(current_user)):
    current_time = int(time_.time())
    button_key = f"button_press:{button_id}"
    status = get_button_status(button_id)

    if status["attempts_left"] == 0:
        raise HTTPException(status_code=429, detail="Лимит нажатий исчерпан")

    if status["last_press_time"] > 0 and (current_time - status["last_press_time"]) < 14400:
        raise HTTPException(status_code=429, detail="Можно нажать через 4 часа")

    # Обновляем Redis
    redis_client.hset(button_key, "last_press", current_time)
    redis_client.hincrby(button_key, "count", 1)

    return {"message": f"Кнопка {button_id} нажата!"}