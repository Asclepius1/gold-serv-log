from typing import List
from datetime import datetime

import requests
from config import BEARER_TOKEN_GOLD_SERV, GOLD_SERV_API_URL
from fastapi import APIRouter, Depends, Query, Request

from auth.db import User
from auth.schemas import UserCreate, UserRead

from sqlalchemy.future import select
from sqlalchemy import Text, cast
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import logs
from models.db import get_async_session
from auth.auth import superuser_required

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
    sort_by: str = Query("datetime"),  # Поле сортировки
    sort_order: str = Query("desc"),  # Направление сортировки ("asc" или "desc")
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(superuser_required),
):
    query = logs.select()

    if owner_name:
        query = query.where(logs.c.owner_name.ilike(f"%{owner_name}%"))
    if file_name:
        query = query.where(logs.c.file_name.ilike(f"%{file_name}%"))
    if message:
        query = query.where(logs.c.message.ilike(f"%{message}%"))
    if log_id:
        # query = query.where(logs.c.id == log_id)
        query = query.filter(logs.c.id.cast(Text).like(str(log_id) + '%'))
    if start_date and end_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.where(logs.c.datetime.between(start_date_obj, end_date_obj))
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
                "color": log.color,
            }
            for log in log_entries
        ],
        "page": page,
        "page_size": page_size,
    }


@router.post("")
async def add_logs(datetime_: str, session: AsyncSession = Depends(get_async_session)):
    
    url = f'{GOLD_SERV_API_URL}/?date={datetime_}'
    headers = {'Authorization': f'Bearer {BEARER_TOKEN_GOLD_SERV}'}
    respone = requests.get(url, headers=headers, verify=False)
    print(respone.status_code)
    if respone.status_code <= 200:
        data: list[dict] = respone.json()
        async with session.begin():
            for log in data:
                try:
                    log_datetime = datetime.strptime(log.get("DatTime"), "%Y-%m-%d %H:%M:%S.%f0")
                except ValueError:
                    return {"error": f"Invalid datetime format for log: {log.get('DatTime')}"}

                query = logs.insert().values(
                    datetime=log_datetime,
                    owner_name=log.get("DepCode"),
                    file_name=log.get("FileName"),
                    message=log.get("Message"),
                    # color=log.get("color", ""),
                )
                await session.execute(query)

        return {"message": f"Logs successfully added"}
    else:
        print(respone.status_code, respone.text)
