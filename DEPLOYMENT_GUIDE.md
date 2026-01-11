# Инструкция по развертыванию и тестированию HR панели

## Требования

- Python 3.10+
- PostgreSQL
- Redis
- FastAPI
- SQLAlchemy

## Установка зависимостей

```bash
pip install -r req.txt
```

## Настройка окружения

Создайте файл `.env` с необходимыми переменными:

```env
# База данных
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/db_name

# Redis (для планировщика)
REDIS_HOST=localhost
REDIS_PASS=password

# FastAPI Users
SECRET=your-secret-key

# Внешние API (если используются)
BEARER_TOKEN_GOLD_SERV=token
GOLD_SERV_API_URL=https://api.example.com
```

## Миграции базы данных

```bash
# Создать миграцию (если ещё не создана)
python -m alembic revision --autogenerate -m "Add HR panel tables"

# Применить миграции
python -m alembic upgrade head
```

## Запуск приложения

### Разработка (с автоперезагрузкой)

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Приложение будет доступно на `http://localhost:8000`

## Инициализация данных для тестирования

### 1. Создание пользователя HR

```bash
# Через admin API (если доступно)
POST /users
{
  "email": "hr@example.com",
  "password": "password123",
  "is_active": true,
  "is_superuser": false
}

# Затем добавить в HR роль
POST /hr/
{
  "user_id": 2
}
```

### 2. Создание директора

```bash
# Сначала создать пользователя
POST /users
{
  "email": "director@example.com",
  "password": "password123",
  "is_active": true,
  "is_superuser": false
}

# Затем назначить его директором склада
POST /warehouse-directors  # endpoint может отличаться
{
  "user_id": 3,
  "location_id": 1
}
```

### 3. Создание локаций

```bash
POST /locations
{
  "location_name": "Склад №1"
}
```

### 4. Создание сотрудников

```bash
POST /employees
{
  "name": "Иван Иванов"
}
```

### 5. Создание owners

```bash
POST /owners
{
  "name": "Петр Петров"
}
```

## Тестирование

### Через curl

```bash
# Авторизация
curl -X POST http://localhost:8000/auth/jwt/login \
  -H "Content-Type: application/json" \
  -d '{"email": "hr@example.com", "password": "password123"}'

# Получение списка директоров
curl -X GET http://localhost:8000/directors/list \
  -H "Cookie: fastapiusersauth=<token>"

# Загрузка локаций
curl -X GET http://localhost:8000/locations/list \
  -H "Cookie: fastapiusersauth=<token>"

# Получение owners локации на дату
curl -X GET "http://localhost:8000/locations/1/assignments?day=2024-01-15" \
  -H "Cookie: fastapiusersauth=<token>"
```

### Через браузер

1. **Откройте** http://localhost:8000
2. **Перейдите** на страницу логина
3. **Введите** email: `hr@example.com`, password: `password123`
4. **Нажмите** "Войти"
5. **Должны** перенаправиться на `/hr`
6. **HR панель** готова к использованию

## Проверка функциональности

### Проверка загрузки директоров

- [ ] Открыть `/hr`
- [ ] Селект "Директор склада" содержит список
- [ ] Выбор директора меняет список локаций

### Проверка загрузки данных

- [ ] Выбрать дату, директора, локацию
- [ ] Нажать "Загрузить"
- [ ] Во всех вкладках появляются данные:
  - Статистика: 5 полей с числами
  - Owners: список текущих + мультиселект
  - Employees: таблица со списком

### Проверка редактирования (текущий день)

- [ ] **Stats tab**: изменить числа → нажать "Сохранить" → данные обновились
- [ ] **Owners tab**: выбрать owners → нажать "Сохранить" → список обновился
- [ ] **Employees tab**: выбрать owner → нажать "Сохранить" → назначение обновилось

### Проверка ограничений (прошедший день, HR)

- [ ] Выбрать прошедший день (например, вчера)
- [ ] Нажать "Загрузить"
- [ ] Проверить:
  - [ ] Поля редактируемы (для HR)
  - [ ] Показано сообщение, что HR может редактировать прошедшие дни
  - [ ] Кнопка "Сохранить" активна

### Проверка прав (суперпользователь)

- [ ] Авторизоваться как суперпользователь
- [ ] Открыть `/hr`
- [ ] Выбрать прошедший день
- [ ] Нажать "Загрузить"
- [ ] Проверить:
  - [ ] Поля включены
  - [ ] Сообщение НЕ показывается
  - [ ] Кнопка "Сохранить" включена
  - [ ] Можно редактировать и сохранять

## Возможные проблемы и решения

### "Нет доступа" при открытии `/hr`

**Причина:** Пользователь не имеет роли HR
**Решение:**

- Проверьте, что в таблице `hrs` есть запись с `user_id` текущего пользователя
- Добавьте роль через API: `POST /hr/`

### "Список директоров пуст"

**Причина:** Нет записей в таблице `warehouse_directors`
**Решение:**

- Создайте пользователей и добавьте их как директоров
- Убедитесь, что привязанные локации существуют

### "Ошибка при подключении к Redis"

**Причина:** Redis не запущен или недоступен
**Решение:**

- Установите Redis: `choco install redis` (Windows) или `brew install redis` (Mac)
- Запустите: `redis-server`
- Или используйте Docker: `docker run -d -p 6379:6379 redis`

### "Ошибка при подключении к БД"

**Причина:** PostgreSQL не запущен или неверные учётные данные
**Решение:**

- Убедитесь, что PostgreSQL запущен
- Проверьте переменные в `.env` файле
- Создайте БД: `createdb db_name`

### Кнопка "Сохранить" не работает

**Причина:** Ошибка в JavaScript или неверный endpoint
**Решение:**

- Откройте DevTools (F12)
- Посмотрите Console на ошибки
- Посмотрите Network на ответы от сервера
- Проверьте, что все endpoints доступны

## Дополнительные команды

### Просмотр логов

```bash
# Все логи приложения в реальном времени
tail -f application.log
```

### Сброс базы данных (ОСТОРОЖНО!)

```bash
# Полный сброс (все данные будут удалены)
python -m alembic downgrade base
python -m alembic upgrade head
```

### Проверка состояния миграций

```bash
python -m alembic current  # текущая версия
python -m alembic history  # история всех миграций
```

## Скрипт для быстрого запуска с тестовыми данными

```python
# test_setup.py
import asyncio
from models.db import get_async_session, engine
from models.models import user, locations, employees, owner, warehouse_directors, hrs
from sqlalchemy import insert

async def setup_test_data():
    async with engine.begin() as conn:
        # Создание таблиц
        from models.models import metadata
        await conn.run_sync(metadata.create_all)

    async for session in get_async_session():
        # Пример данных - заполните по необходимости
        pass

if __name__ == "__main__":
    asyncio.run(setup_test_data())
```

Запуск:

```bash
python test_setup.py
```

## Контрольный список для сдачи

- [ ] Все миграции применены
- [ ] Приложение запускается без ошибок
- [ ] HR пользователь может открыть `/hr`
- [ ] Директор может открыть `/director`
- [ ] Суперпользователь может открыть обе страницы
- [ ] Можно загружать и редактировать данные на текущий день
- [ ] Ограничения по датам работают корректно
- [ ] Данные сохраняются в БД
- [ ] Все API endpoints отвечают корректно
- [ ] Нет ошибок в консоли браузера
