from typing import AsyncGenerator
from config import DATABASE_URL, REDIS_PASS, REDIS_HOST
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


import redis

redis_client = redis.Redis(host=REDIS_HOST, db=0, decode_responses=True, password=REDIS_PASS)

def set_autorefresh_state(state: bool):
    redis_client.set("autorefresh", str(state))

# Функция для получения состояния
def get_autorefresh_state():
    return redis_client.get("autorefresh") == "True"