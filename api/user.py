from fastapi import APIRouter, Depends, Request
from typing import List
from auth.db import User
from auth.schemas import UserCreate, UserRead

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import get_async_session
from auth.auth import superuser_required

router = APIRouter(prefix="", tags=["users"])

@router.get("/users", response_model=List[UserRead])
async def get_all_users(
    session: AsyncSession = Depends(get_async_session), 
    user: User = Depends(superuser_required) 
):
    query = select(User)
    result = await session.execute(query)
    users = result.scalars().all()
    return users