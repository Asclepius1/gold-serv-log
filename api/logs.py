from datetime import datetime, time, timedelta

import httpx
import requests
from config import BEARER_TOKEN_GOLD_SERV, GOLD_SERV_API_URL
from fastapi import APIRouter, Depends, HTTPException, Query

from auth.db import User

from sqlalchemy.future import select
from sqlalchemy import Text, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import logs, log_filters, log_errors
from models.db import get_async_session, get_autorefresh_state, set_autorefresh_state
from auth.auth import superuser_required, current_user
from schedule import update_scheduler
from models.schemas import ErrorSchema

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
    print(log_entries[0].message)
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

@router.post("/apply-errors-to-logs")
async def apply_errors_to_logs(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(superuser_required),
):
    # Получение всех правил из таблицы ошибок
    error_rules_query = select(log_errors)
    result = await session.execute(error_rules_query)
    error_rules = result.fetchall()

    if not error_rules:
        raise HTTPException(status_code=404, detail="Правила ошибок отсутствуют.")

    # Применение правил ко всем логам
    logs_query = select(logs)
    logs_result = await session.execute(logs_query)
    logs_data = logs_result.fetchall()

    updates = []
    for log in logs_data:
        for rule in error_rules:
            if rule.error_message in log.message:
                updates.append({
                    "id": log.id,
                    "error_type": rule.error_type,
                    "color": rule.color,
                })
                break  # Применяем только первое совпадение

    # Обновление логов
    for update in updates:
        await session.execute(
            logs.update()
            .where(logs.c.id == update["id"])
            .values(
                error_type=update["error_type"],
                color=update["color"]
            )
        )

    await session.commit()
    return {"message": f"Ошибки применены к {len(updates)} логам."}


def get_current_data(data: list[dict], last_log: dict) -> list[dict]:
    correct_data_to_import = []
    for log in data:
        log_datetime = datetime.strptime(log.get("DatTime"), "%Y-%m-%d %H:%M:%S.%f0")
        if log_datetime >= last_log.get("datetime") and last_log.get('file_name') != log.get("FileName"):
            correct_data_to_import.append(log)
    return correct_data_to_import

    
async def run_add_logs():
    await _add_logs_wrapper()

async def _add_logs_wrapper():
    async for session in get_async_session():
        await add_logs(session=session)


async def get_error_mapping_check_error(session: AsyncSession):
    query = select(log_errors.c.error_message, log_errors.c.color, log_errors.c.error_type)
    result = await session.execute(query)
    return {row.error_message: (row.color, row.error_type) for row in result.fetchall()}

async def check_error(message: str, session: AsyncSession):
    # Загружаем ошибки и их параметры из базы данных
    error_mapping = await get_error_mapping_check_error(session)

    for substring, (color, error_type) in error_mapping.items():
        if substring in message:
            return color, error_type

    return "green", "-"


@router.post("/error")
async def add_or_update_error(
    error_data: ErrorSchema,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(superuser_required),
):
    valid_colors = ["yellow", "red", "green"]
    if error_data.color not in valid_colors:
        raise HTTPException(status_code=400, detail="Invalid color")

    # Проверка существования ошибки
    existing_error = await session.execute(
        select(log_errors).where(log_errors.c.error_message == error_data.error_message)
    )
    existing_error = existing_error.fetchone()

    if existing_error:
        # Обновляем существующую ошибку
        query = (
            log_errors.update()
            .where(log_errors.c.error_message == error_data.error_message)
            .values(color=error_data.color, error_type=error_data.error_type)
        )
    else:
        # Добавляем новую ошибку
        query = log_errors.insert().values(
            error_message=error_data.error_message,
            color=error_data.color,
            error_type=error_data.error_type,
        )

    await session.execute(query)
    await session.commit()

    return {"message": f"Error '{error_data.error_message}' has been added/updated with color '{error_data.color}' and type '{error_data.error_type}'."}

@router.get("/error-mapping")
async def get_error_mapping(session: AsyncSession = Depends(get_async_session)):
    query = select(log_errors)
    result = await session.execute(query)
    errors = result.fetchall()

    return [{"id": error.id, "message": error.error_message, "color": error.color, "error_type": error.error_type} for error in errors]

@router.post("/error/delete")
async def delete_errors(
    error_ids: list[int],  # Получаем список ID ошибок
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(superuser_required),
):
    if not error_ids:
        raise HTTPException(status_code=400, detail="Список ID ошибок пуст.")

    # Удаление ошибок из базы данных
    await session.execute(
        log_errors.delete().where(log_errors.c.id.in_(error_ids))
    )
    await session.commit()

    return {"message": f"Удалено {len(error_ids)} ошибок."}

# только в крайних случаях, могу быть дубликаты если использовать этот ендпойнт
# @router.post("/add_old_logs")
# async def add_old_logs(
#     date_str: str,
#     session: AsyncSession = Depends(get_async_session),
#     user: User = Depends(superuser_required),
# ):
#     # date_range = ['17012025', '18012025', '19012025', '20012025', '21012025', '22012025']
#     url = f"{GOLD_SERV_API_URL}/?date={date_str}"

#     headers = {'Authorization': f'Bearer {BEARER_TOKEN_GOLD_SERV}'}
#     async with httpx.AsyncClient(verify=False) as client:
#         try:
#             response = await client.get(url, headers=headers)
#             response.raise_for_status()
#         except httpx.HTTPStatusError as exc:
#             raise HTTPException(
#                 status_code=exc.response.status_code,
#                 detail=f"Ошибка HTTP: {exc.response.status_code}, текст ответа: {exc.response.text}",
#             )
#         except httpx.RequestError as exc:
#             raise HTTPException(
#                 status_code=500,
#                 detail=f"Не удалось подключиться к серверу: {exc}",
#             )

#         # Обрабатываем данные
#         data: list[dict] = response.json()

#         for log in data:
#             try:
#                 log_datetime = datetime.strptime(log.get("DatTime"), "%Y-%m-%d %H:%M:%S.%f0")
#             except ValueError:
#                 return {"error": f"Некорректный формат даты/времени: {log.get('DatTime')}"}

#             color, error_type = await check_error(log.get("Message"), session)

#             query = logs.insert().values(
#                 datetime=log_datetime,
#                 owner_name=log.get("DepCode"),
#                 file_name=log.get("FileName"),
#                 message=log.get("Message"),
#                 error_type=error_type,
#                 color=color,
#             )
#             try:
#                 await session.execute(query)
#             except Exception as e:
#                 raise HTTPException(
#                     status_code=500,
#                     detail=f"Ошибка при добавлении записи в базу данных: {e}",
#                 )

#     await session.commit()
#     print(f"Логи импортированы корректно, количество строк: {len(data)}")
#     return {"message": f"Логи импортированы корректно, количество строк: {len(data)}"}

@router.post("/add_logs")
async def add_logs(
    datetime_: str | None = None,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(superuser_required),
):
    print(f"Началось добавление логов дата:{datetime_}")
    # Получаем последний лог
    latest_current_log_query = select(logs).order_by(logs.c['datetime'].desc()).limit(1)
    result = await session.execute(latest_current_log_query)
    latest_current_log = result.fetchone()

    if not latest_current_log:
        return {"message": "Нет предыдущих логов в базе данных"}

    # Формируем URL
    date_str = datetime_ or datetime.now().strftime('%d%m%Y')
    url = f"{GOLD_SERV_API_URL}/?date={date_str}"

    # Выполняем запрос к серверу
    headers = {'Authorization': f'Bearer {BEARER_TOKEN_GOLD_SERV}'}
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Ошибка HTTP: {exc.response.status_code}, текст ответа: {exc.response.text}",
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Не удалось подключиться к серверу: {exc}",
            )

    # Обрабатываем данные
    data: list[dict] = response.json()
    correct_data = get_current_data(
        data,
        {'datetime': latest_current_log.datetime, 'file_name': latest_current_log.file_name},
    )

    if not correct_data:
        print("Нет данных для импорта")
        return {"message": "Нет данных для импорта"}

    for log in correct_data:
        try:
            log_datetime = datetime.strptime(log.get("DatTime"), "%Y-%m-%d %H:%M:%S.%f0")
        except ValueError:
            return {"error": f"Некорректный формат даты/времени: {log.get('DatTime')}"}

        color, error_type = await check_error(log.get("Message"), session)

        query = logs.insert().values(
            datetime=log_datetime,
            owner_name=log.get("DepCode"),
            file_name=log.get("FileName"),
            message=log.get("Message"),
            error_type=error_type,
            color=color,
        )
        try:
            await session.execute(query)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при добавлении записи в базу данных: {e}",
            )

    await session.commit()
    print(f"Логи импортированы корректно, количество строк: {len(correct_data)}")
    return {"message": f"Логи импортированы корректно, количество строк: {len(correct_data)}"}



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
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session)
):
    query = select(log_filters).where(log_filters.c.user_id == user.id)
    result = await session.execute(query)
    filter_data = result.first()
    return filter_data.filters if filter_data else {}

@router.post("/set_autorefresh")
async def set_autorefresh(state: bool, user: User = Depends(superuser_required)):
    set_autorefresh_state(state)
    await update_scheduler()  # Обновляем планировщик
    return {"autorefresh": state}

@router.get("/get_autorefresh")
async def get_autorefresh(user: User = Depends(superuser_required)):
    state = get_autorefresh_state()
    return {"autorefresh": state}