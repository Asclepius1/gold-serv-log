from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase, SQLAlchemyBaseUserTable
from models.db import get_async_session
from sqlalchemy import Boolean, Integer, String, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from models.models import owner


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTable[int], Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(length=320), nullable=False)
    owners_id: Mapped[int] = mapped_column(Integer, ForeignKey(owner.c.id), nullable=True)
    is_hr: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)