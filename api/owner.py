import httpx
import requests
import models.schemas as sch
from models.models import owner, owner_report_access
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from auth.db import User
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import get_async_session
from auth.auth import superuser_required, current_user
from config import BEARER_TOKEN_GOLD_SERV, GOLD_SERV_API_URL

router = APIRouter(prefix="/owners", tags=["owners"])

@router.get("/update-all/")
async def check_all_owner_and_add(session: AsyncSession = Depends(get_async_session), user: User = Depends(superuser_required)):
    url = f"{GOLD_SERV_API_URL}/?depositor=DEPLIST"
    headers = {'Authorization': f'Bearer {BEARER_TOKEN_GOLD_SERV}'}

    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            if data := response.json():
                owner_list = data.get('DeposCode', [])
                # Проверяем, какие владельцы уже есть в базе данных
                existing_owners_query = select(owner).filter(owner.c.name.in_(owner_list))
                result = await session.execute(existing_owners_query)
                existing_owners = {row.name for row in result.fetchall()}

                # Фильтруем новых владельцев, чтобы не добавлять тех, кто уже есть в базе
                new_owners = [owner for owner in owner_list if owner not in existing_owners]

                if new_owners:
                    # Добавляем новых владельцев в базу данных
                    new_owners_data = [{'name': owner} for owner in new_owners]
                    await session.execute(owner.insert(), new_owners_data)
                    await session.commit()
                    return {"message": f"Владельцы были добавлены в количестве: {len(new_owners)}"}
                return {'message': 'Нет новых данных для вставки'}
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"HTTP Error: {exc.response.text}")
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Request failed: {str(exc)}")

    raise HTTPException(status_code=404, detail="Не получилось добавить владельцев")


@router.post("", response_model=sch.OwnerRead)
async def create_owner(owner_data: sch.OwnerCreate, session: AsyncSession = Depends(get_async_session), 
        user: User = Depends(superuser_required)):
    
    query = owner.insert().values(name=owner_data.name).returning(owner)
    result = await session.execute(query)
    new_owner = result.fetchone()  # Получаем созданную запись
    await session.commit()
    return new_owner

@router.get("", response_model=List[sch.OwnerRead])
async def read_owners(session: AsyncSession = Depends(get_async_session),  user: User = Depends(current_user)):
    query = select(owner)
    result = await session.execute(query)
    owners = result.mappings().all()
    return owners


@router.get("/reports/{report_id}")
async def get_owners_with_access(
    report_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(superuser_required),
):
    # Получаем всех владельцев
    owners_query = select(owner.c.id, owner.c.name)
    owners_result = await session.execute(owners_query)
    owners = owners_result.fetchall()

    # Получаем владельцев с доступом к отчету
    access_query = select(
        owner_report_access.c.owner_id, owner_report_access.c.is_disabled
    ).where(owner_report_access.c.report_id == report_id)
    access_result = await session.execute(access_query)
    access_data = {record.owner_id: record.is_disabled for record in access_result.fetchall()}

    # Формируем список владельцев с указанием состояния доступа
    return [
        {
            "id": owner.id,
            "name": owner.name,
            "has_access": access_data.get(owner.id, True),  # False, если доступ отключен
        }
        for owner in owners
    ]

@router.get("/{owner_id}", response_model=sch.OwnerRead)
async def read_owner(owner_id: int, session: AsyncSession = Depends(get_async_session), user: User = Depends(current_user)):
    
    db_owner = select(owner).where(owner.c.id == owner_id)
    result = await session.execute(db_owner)
    owners = result.mappings().first()
    if owners is None:
        raise HTTPException(status_code=404, detail="Владелец не найден")
    return owners

@router.put("/{owner_id}", response_model=sch.OwnerRead)
async def update_owner(owner_id: int, owner_update: sch.OwnerUpdate, session: AsyncSession = Depends(get_async_session), user: User = Depends(superuser_required),):
    query = select(owner).where(owner.c.id == owner_id)
    result = await session.execute(query)
    db_owner = result.fetchone()

    if db_owner is None:
        raise HTTPException(status_code=404, detail="Владелец не найден")
    
    update_data = owner_update.model_dump(exclude_unset=True)

    if update_data:
        query = (
            update(owner)
            .where(owner.c.id == owner_id)
            .values(**update_data)
            .returning(owner)
        )
        result = await session.execute(query)
        await session.commit()
        return result.fetchone()
    raise HTTPException(status_code=400, detail="Нет данных для обновления")

@router.delete("/{owner_id}")
async def delete_owner(owner_id: int, session: AsyncSession = Depends(get_async_session), user: User = Depends(superuser_required)):
    query = delete(owner).where(owner.c.id == owner_id)
    await session.execute(query)
    await session.commit()

    return {"message": f"Владелец с id {owner_id} удалена!"}

