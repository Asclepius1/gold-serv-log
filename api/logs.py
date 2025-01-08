import asyncio
from typing import List
from datetime import datetime, time

import requests
from config import BEARER_TOKEN_GOLD_SERV, GOLD_SERV_API_URL
from fastapi import APIRouter, Depends, Query, Request

from auth.db import User
from auth.schemas import UserCreate, UserRead

from sqlalchemy.future import select
from sqlalchemy import Text, cast, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import logs, log_filters
from models.db import get_async_session, get_autorefresh_state, set_autorefresh_state
from auth.auth import superuser_required
from schedule import update_scheduler

router = APIRouter(prefix="/logs", tags=["logs"])

@router.get("")
async def get_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    owner_name: str = Query(None),
    file_name: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    message: str = Query(None),  # Фильтр по сообщению
    log_id: int = Query(None),  # Фильтр по ID
    error_type: str = Query(None),
    color: str = Query(None),
    sort_by: str = Query("datetime"),  # Поле сортировки
    sort_order: str = Query("desc"),  # Направление сортировки ("asc" или "desc")
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(superuser_required),
):
    query = logs.select()

    if color:
        query = query.where(logs.c.color == color)
    if error_type:
        query = query.where(logs.c.error_type.ilike(f"%{error_type}%"))
    if owner_name:
        # query = query.where(logs.c.owner_name.ilike(f"%{owner_name}%"))
        owner_names = [name.strip() for name in owner_name.split(",")]
        if not owner_names[-1]:
            owner_names.pop(-1)
        query = query.where(or_(*[logs.c.owner_name.ilike(f"%{name}%") for name in owner_names]))
    if file_name:
        query = query.where(logs.c.file_name.ilike(f"%{file_name}%"))
    if message:
        query = query.where(logs.c.message.ilike(f"%{message}%"))
    if log_id:
        # query = query.where(logs.c.id == log_id)
        query = query.filter(logs.c.id.cast(Text).like(str(log_id) + '%'))
    if start_date and end_date:
        try:
            start_date_obj = datetime.combine(datetime.strptime(start_date, "%Y-%m-%d"), time(0, 0))
            end_date_obj = datetime.combine(datetime.strptime(end_date, "%Y-%m-%d"), time(23, 59, 59))
            query = query.where(logs.c.datetime >= start_date_obj, logs.c.datetime <= end_date_obj)
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD."}

    # Сортировка
    if sort_by in logs.c:
        order_by_column = logs.c[sort_by]
        if sort_order == "desc":
            order_by_column = order_by_column.desc()
        query = query.order_by(order_by_column)

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await session.execute(query)
    log_entries = result.fetchall()

    return {
        "data": [
            {
                "id": log.id,
                "datetime": log.datetime,
                "owner_name": log.owner_name,
                "file_name": log.file_name,
                "message": log.message,
                "error_type": log.error_type,
                "color": log.color,
            }
            for log in log_entries
        ],
        "page": page,
        "page_size": page_size,
    }


def get_current_data(data: list[dict], last_log: dict) -> list[dict]:
    correct_data_to_import = []
    for log in data:
        log_datetime = datetime.strptime(log.get("DatTime"), "%Y-%m-%d %H:%M:%S.%f0")
        if log_datetime >= last_log.get("datetime") and last_log.get('file_name') != log.get("FileName"):
            correct_data_to_import.append(log)
    return correct_data_to_import

    
async def run_add_logs():
    # asyncio.run(_add_logs_wrapper())
    await _add_logs_wrapper()

async def _add_logs_wrapper():
    async for session in get_async_session():
        await add_logs(session=session)


def check_error(message: str):
    error_mapping = {
        "Fields not replaced": ("yellow", "Fields not replaced"),
        "Код 53236_101 уже присутствует": ("red", "Код уже присутствует"),
    }

    for substring, (color, error_type) in error_mapping.items():
        if substring in message:
            return color, error_type

    return "green", "-"

@router.post("")
async def add_logs(datetime_: str|None = None, session: AsyncSession = Depends(get_async_session)):
    
    latest_current_log = logs.select().order_by(logs.c['datetime'].desc()).limit(1)
    result = await session.execute(latest_current_log)
    latest_current_log = result.fetchone()
    print(latest_current_log)
    url = f'{GOLD_SERV_API_URL}'
    if datetime_:
        url+=f'/?date={datetime_}'
    else:
        url+=f"/?date={datetime.now().strftime("%d%m%Y")}"

    headers = {'Authorization': f'Bearer {BEARER_TOKEN_GOLD_SERV}'}
    respone = requests.get(url, headers=headers, verify=False)
    print(respone.status_code)
    
    if respone.status_code == 200:
        data: list[dict] = respone.json()
        correct_data = get_current_data(data, {'datetime': latest_current_log.datetime, 'file_name': latest_current_log.file_name})
        if correct_data:
            for log in correct_data:
                try:
                    log_datetime = datetime.strptime(log.get("DatTime"), "%Y-%m-%d %H:%M:%S.%f0")
                except ValueError:
                    return {"error": f"Invalid datetime format for log: {log.get('DatTime')}"}
                
                color, error_type = check_error(log.get("Message"))

                query = logs.insert().values(
                    datetime=log_datetime,
                    owner_name=log.get("DepCode"),
                    file_name=log.get("FileName"),
                    message=log.get("Message"),
                    error_type=error_type,
                    color=color,
                )
                await session.execute(query)
            await session.commit()
            return {"message": f"Логи импортированы корректно, кол-во строк: {len(correct_data)}"}
        return {"message": f'Нет данных для имопрта'}
    else:
        print(respone.status_code, respone.text)



@router.post("/filters")
async def save_filters(
    filters: dict, 
    user: User = Depends(superuser_required),
    session: AsyncSession = Depends(get_async_session)
):
    query = select(log_filters).where(log_filters.c.user_id == user.id)
    result = await session.execute(query)
    existing_filter = result.first()

    if existing_filter:
        await session.execute(
            log_filters.update()
            .where(log_filters.c.user_id == user.id)
            .values(filters=filters)
        )
    else:
        await session.execute(
            log_filters.insert().values(user_id=user.id, filters=filters)
        )

    await session.commit()
    return {"message": "Filters saved"}

@router.get("/filters")
async def get_filters(
    user: User = Depends(superuser_required),
    session: AsyncSession = Depends(get_async_session)
):
    query = select(log_filters).where(log_filters.c.user_id == user.id)
    result = await session.execute(query)
    filter_data = result.first()
    return filter_data.filters if filter_data else {}

@router.post("/set_autorefresh")
async def set_autorefresh(state: bool):
    set_autorefresh_state(state)
    await update_scheduler()  # Обновляем планировщик
    return {"autorefresh": state}

@router.get("/get_autorefresh")
async def get_autorefresh():
    state = get_autorefresh_state()
    return {"autorefresh": state}