import asyncio
from fastapi import FastAPI
from models.db import init_redis
import pytz
from models.db import get_autorefresh_state
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from contextlib import asynccontextmanager
from utils.logger_config import cleanup_old_logs, get_logger

from config import REDIS_HOST, REDIS_PASS

timezone_almaty = pytz.timezone('Asia/Almaty')
logger = get_logger("scheduler")

import sys

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


jobstores = {
    'default': RedisJobStore(host=REDIS_HOST, db=0, password=REDIS_PASS)
}

scheduler = AsyncIOScheduler(jobstores=jobstores)

# Асинхронные обёртки для задач
async def delete_old_files_task():
    """Асинхронная обёртка для удаления старых файлов"""
    from api.files import delete_old_files
    try:
        await delete_old_files()
        logger.info("✅ Удаление старых файлов выполнено успешно")
    except Exception as e:
        logger.error(f"❌ Ошибка при удалении старых файлов: {str(e)}", exc_info=True)

async def cleanup_logs_task():
    """Асинхронная обёртка для очистки логов"""
    try:
        cleanup_old_logs()
        logger.info("✅ Очистка логов выполнена успешно")
    except Exception as e:
        logger.error(f"❌ Ошибка при очистке логов: {str(e)}", exc_info=True)

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
    
    # Настраиваем параметры scheduler для правильной работы
    scheduler.configure(
        job_defaults={'coalesce': True, 'max_instances': 1},
        misfire_grace_time=300  # 5 минут - если запуск пропущен, но в пределах этого времени, всё равно запустить
    )
    
    scheduler.start()
    print("Планировщик запущен")
    
    # Задача удаления старых файлов (каждый день в полночь)
    scheduler.add_job(
        delete_old_files_task, 
        "cron", 
        hour=0, 
        minute=0, 
        timezone=timezone_almaty,
        id="delete_old_files_job",
        coalesce=True,  # Объединить пропущенные запуски в один
        misfire_grace_time=300  # 5 минут
    )
    logger.info("📁 Задача удаления старых файлов добавлена (каждый день в 00:00)")
    
    # Задача очистки старых логов (каждый день в 00:30)
    scheduler.add_job(
        cleanup_logs_task, 
        "cron", 
        hour=0, 
        minute=30, 
        timezone=timezone_almaty,
        id="cleanup_logs_job",
        coalesce=True,  # Объединить пропущенные запуски в один
        misfire_grace_time=300  # 5 минут
    )
    logger.info("🗑️ Задача очистки логов добавлена (каждый день в 00:30)")

    await update_scheduler()

    yield  # Даем FastAPI стартовать

    scheduler.shutdown()
    print("Планировщик остановлен")