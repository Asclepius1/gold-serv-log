import os
import time as time_
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List

from fastapi.responses import FileResponse
import requests
from config import BEARER_TOKEN_GOLD_SERV, GOLD_SERV_API_URL
from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import AccessChanges, ReportCreate
from models.models import files, reports, owner_report_access, owner as owner_db
from models.db import get_async_session, redis_client
from auth.auth import current_user, superuser_required
from auth.db import User

router = APIRouter(prefix="/files", tags=["files"], )

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.get("/reports")
async def get_reports(session: AsyncSession = Depends(get_async_session), user: User = Depends(superuser_required)):
    # Выполняем запрос для получения всех отчетов
    query = select(reports)
    result = await session.execute(query)
    reports_data = result.fetchall()
    if reports_data:
        # Возвращаем список отчетов в формате JSON
        return [
            {
                "id": item.id,
                "name": item.name,
                "param": item.param,
            }
            for item in reports_data
        ]
    
    # Если нет отчетов, возвращаем пустой список
    return [
        {
            "id": None,
            "name": '-',
            "param": '-',
        }
    ]

@router.post("/reports")
async def add_report(report: ReportCreate, session: AsyncSession = Depends(get_async_session), user: User = Depends(superuser_required)):
    query = reports.insert().values(name=report.name, param=report.param)
    await session.execute(query)
    await session.commit()
    return {"message": "Успешно добавлено"}

@router.post("/upload/")
async def upload_files(owner_id: int, session: AsyncSession = Depends(get_async_session), user: User = Depends(current_user)):
    # Проверяем наличие владельца
    owner_result = await session.execute(owner_db.select().where(owner_db.c.id == owner_id))
    owner = owner_result.fetchone()

    if not owner:
        raise HTTPException(status_code=404, detail="Владелец не найден")

    # Получаем список активных параметров (param) для владельца
    query = (
        select(reports.c.param, reports.c.name)
        .select_from(owner_report_access.join(reports, owner_report_access.c.report_id == reports.c.id))
        .where(owner_report_access.c.owner_id == owner_id, owner_report_access.c.is_disabled == False)
    )
    result = await session.execute(query)
    params = result.scalars().all()
    
    print(params)

    if not params:
        raise HTTPException(status_code=404, detail="Нет активных отчетов для владельца")
    
    # Скачиваем файлы для каждого param
    saved_files = []
    for param, name in params:
        url = f"{GOLD_SERV_API_URL}/?{param}={owner.name}"
        print(url)
        headers = {'Authorization': f'Bearer {BEARER_TOKEN_GOLD_SERV}'}
        response = requests.get(url, headers=headers, verify=False)

        if response.status_code == 200:
            owner_dir = UPLOAD_DIR / owner.name
            owner_dir.mkdir(parents=True, exist_ok=True)

            now = datetime.now().strftime("%d%m%Y_%H%M%S")
            rand = "".join([str(random.randint(0, 9)) for _ in range(8)])
            file_path = owner_dir / f"{owner.name}_{name}_{now}_({rand}).xlsx"

            with open(file_path, "wb") as f:
                f.write(response.content)

            print(f"Файл сохранен как {file_path}")
            saved_files.append(file_path)

            # Добавляем информацию о файле в БД
            query = files.insert().values(
                owner_id=owner_id,
                filename=file_path.name,
                file_path=str(file_path)
            )
            await session.execute(query)
        else:
            print(f"Ошибка при запросе {url}: {response.status_code}")

    await session.commit()

    if not saved_files:
        raise HTTPException(status_code=404, detail="Файлы не были загружены")

    return {"message": "Файлы успешно добавлены", "files": [str(file) for file in saved_files]}




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
async def get_file_path_by_owner_id(
    owner_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user),
):
    result = await session.execute(files.select().where(files.c.owner_id == owner_id).order_by(files.c.created_at.desc()))
    files_data = result.scalars()
    
    if files_data:
        return [
            {
                "id": item.id,
                "name": item.filename,
                "date": item.created_at,
                "type": "file",
            } for item in result
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

    # Если прошло 12 часов с первого нажатия, сбрасываем счетчик
    if press_count >= 1 and (current_time - last_press_time) >= 43200:
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


@router.delete("/reports/{report_id}")
async def delete_link(report_id: int, session: AsyncSession = Depends(get_async_session), user: User = Depends(superuser_required)):
    query = reports.delete().where(reports.c.id == report_id)
    await session.execute(query)
    await session.commit()
    return {"message": "Отчет успешно удален"}

@router.post("/reports/{report_id}/access")
async def update_report_access(
    report_id: int,
    access_changes: AccessChanges,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(superuser_required),
):
    print(access_changes)
    return {"message": "Доступ успешно обновлен"}
    for change in access_changes:
        owner_id = change.owner_id
        has_access = change.has_access

        # Проверяем существующую запись
        query = owner_report_access.select().where(
            owner_report_access.c.report_id == report_id,
            owner_report_access.c.owner_id == owner_id,
        )
        result = await session.execute(query)
        record = result.fetchone()

        if record:
            # Обновляем запись
            update_query = owner_report_access.update().where(
                owner_report_access.c.id == record.id
            ).values(is_disabled=not has_access)
            await session.execute(update_query)
        else:
            # Добавляем новую запись
            insert_query = owner_report_access.insert().values(
                owner_id=owner_id,
                report_id=report_id,
                is_disabled=not has_access,
            )
            await session.execute(insert_query)

    await session.commit()
    return {"message": "Доступ успешно обновлен"}