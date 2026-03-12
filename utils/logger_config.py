"""
Конфигурация логирования для приложения.
Логирует все события в файлы по датам.
Автоматически очищает логи старше 14 дней.
"""

import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Максимальное количество дней для хранения логов
LOGS_RETENTION_DAYS = 14


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Инициализация логирования с ротацией по дням.
    
    Args:
        name: Имя логгера
        level: Уровень логирования (по умолчанию INFO)
        
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    
    # Если логгер уже настроен, возвращаем его
    if logger.hasHandlers():
        return logger
    
    logger.setLevel(level)
    
    # Имя логфайла по текущему дню
    log_file = LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    
    # Форматер с полной информацией
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для файла
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Обработчик для консоли (только WARNING и выше)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def cleanup_old_logs(days_to_keep: int = LOGS_RETENTION_DAYS) -> None:
    """
    Удаляет логи старше указанного количества дней.
    
    Args:
        days_to_keep: Количество дней для хранения логов (по умолчанию 14)
    """
    if not LOGS_DIR.exists():
        return
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    deleted_count = 0
    
    for log_file in LOGS_DIR.glob("*.log"):
        try:
            file_date = datetime.strptime(log_file.stem, '%Y-%m-%d')
            if file_date < cutoff_date:
                log_file.unlink()
                deleted_count += 1
        except ValueError:
            # Пропускаем файлы с неправильным форматом имени
            continue
    
    if deleted_count > 0:
        logger = logging.getLogger("logger_config")
        logger.info(f"Удалено {deleted_count} старых логфайлов (старше {days_to_keep} дней)")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Получить или создать логгер.
    
    Args:
        name: Имя логгера (по умолчанию используется имя модуля)
        
    Returns:
        Логгер
    """
    if name is None:
        name = "app"
    return setup_logger(name)
