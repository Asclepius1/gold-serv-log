import asyncio
from fastapi import FastAPI
from models.db import init_redis
import pytz
from models.db import get_autorefresh_state
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from contextlib import asynccontextmanager

from config import REDIS_HOST, REDIS_PASS

timezone_almaty = pytz.timezone('Asia/Almaty')

import sys

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


jobstores = {
    'default': RedisJobStore(host=REDIS_HOST, db=0, password=REDIS_PASS)
}

scheduler = AsyncIOScheduler(jobstores=jobstores)

async def update_scheduler():
    """Обновляет задачи в планировщике в зависимости от состояния autorefresh."""
    from api.logs import run_add_logs
    
    global scheduler
    
    autorefresh = get_autorefresh_state()
    
    # Удаляем старую задачу (если она есть)
    for job in scheduler.get_jobs():
        if job.id == "autorefresh_job":
            scheduler.remove_job(job.id)

    if autorefresh:
        print("Автообновление включено: Запускаем задачу каждые 15 минут")
        scheduler.add_job(run_add_logs, "interval", minutes=15, id="autorefresh_job", timezone=timezone_almaty)
    else:
        print("Автообновление отключено: Используем стандартные настройки")
        scheduler.add_job(run_add_logs, 'cron', hour=7, minute=0, timezone=timezone_almaty)
        scheduler.add_job(run_add_logs, 'cron', hour=13, minute=20, timezone=timezone_almaty)
        scheduler.add_job(run_add_logs, 'cron', hour=18, minute=20, timezone=timezone_almaty)
        # scheduler.add_job(run_add_logs, 'date', run_date=datetime.now())


@asynccontextmanager
async def lifespan(app: FastAPI):

    await init_redis()
    print("FastAPILimiter инициализирован")
    from api.files import delete_old_files
    scheduler.start()
    print("Планировщик запущен")
    
    scheduler.add_job(delete_old_files, "cron", hour=0, minute=0, timezone=timezone_almaty)

    await update_scheduler()

    yield  # Даем FastAPI стартовать

    scheduler.shutdown()
    print("Планировщик остановлен")