import asyncio
import os
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
from models.db import get_async_session, get_autorefresh_state, set_autorefresh_state
from auth.auth import superuser_required
from schedule import update_scheduler

router = APIRouter(prefix="/files", tags=["files"])

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
async def upload_file(owner_id: int, session: AsyncSession = Depends(get_async_session)):
    
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
async def download_file(file_id: int, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(files.select().where(files.c.id == file_id))
    file = result.fetchone()
    if file:
        file_path = Path(file.file_path)
        if file_path.exists():
            return FileResponse(file_path, filename=file.filename)
    raise HTTPException(status_code=404, detail="Файл не найден")

async def delete_old_files():
    async with get_async_session() as session:
        threshold_date = datetime.now() - timedelta(days=30)

        # Получаем только `file_path` и `id`, чтобы не загружать лишние данные
        result = await session.execute(select(files.c.id, files.c.file_path).where(files.c.created_at < threshold_date))
        old_files = result.all()

        if not old_files:
            return  # Если старых файлов нет, ничего не делаем

        # Удаляем файлы из системы
        for file_id, file_path in old_files:
            file_path = Path(file_path)
            if file_path.exists():
                os.remove(file_path)

        # Удаляем файлы из базы за 1 SQL-запрос (оптимизировано)
        await session.execute(files.delete().where(files.c.id.in_([file_id for file_id, _ in old_files])))
        await session.commit()

@router.get("/{owner_id}")
async def get_file_path_by_owner_id(owner_id: int, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(files.select().where(files.c.owner_id == owner_id))
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