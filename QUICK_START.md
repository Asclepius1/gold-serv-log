# ⚡ Одноминутный гайд - Быстрый старт

## 🚀 За 60 секунд

### 1️⃣ Установка (15 сек)

```bash
pip install -r req.txt
```

### 2️⃣ Переменные окружения (15 сек)

```bash
# Создайте .env файл с:
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
REDIS_HOST=localhost
REDIS_PASS=password
```

### 3️⃣ Миграция БД (15 сек)

```bash
python -m alembic upgrade head
```

### 4️⃣ Запуск (15 сек)

```bash
uvicorn main:app --reload
```

### 5️⃣ Открыть (1 сек)

```
http://localhost:8000
```

---

## 👤 Быстрый тест

### Авторизоваться как HR

```
email: hr@example.com
password: password123
```

### Вы увидите

```
✅ Редирект на /hr
✅ HR панель с 3 вкладками
✅ Селект директора и локации
✅ Фильтр по дате
```

### Попробуйте

1. Выбрать директора → локация загружается
2. Выбрать дату (сегодня)
3. Нажать "Загрузить"
4. Отредактировать статистику
5. Нажать "Сохранить"
6. Проверить что обновилось

---

## ❌ Если не работает

### Ошибка подключения к Redis

```bash
docker run -d -p 6379:6379 redis
```

### Ошибка в БД

```bash
# Проверить миграции
python -m alembic current

# Откатить и заново
python -m alembic downgrade base
python -m alembic upgrade head
```

### Нет доступа к `/hr`

```bash
# Добавить роль HR пользователю
# Через API: POST /hr/ с user_id
```

---

## 📚 Дальше читайте

- **Как использовать** → [HR_PANEL_USAGE.md](./HR_PANEL_USAGE.md)
- **Как устроено** → [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Как развернуть** → [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- **Что изменилось** → [CHANGES_SUMMARY.md](./CHANGES_SUMMARY.md)

---

## ✅ Статус

**ГОТОВО К РАБОТЕ ✅**
