# Архитектура HR панели управления

## Структура проекта

### Backend (API)

#### Маршруты

- `GET /hr` - страница HR панели (с проверкой доступа)
- `GET /director` - страница директора (с проверкой доступа)
- Остальные API endpoints с префиксом `/`

#### API модули

**api/hr.py**

- `GET /hr/` - список HR пользователей (суперпользователь только)
- `POST /hr/` - добавить HR пользователя (суперпользователь только)
- `DELETE /hr/{user_id}` - удалить HR пользователя (суперпользователь только)
- `GET /hr/me` - проверить, является ли текущий пользователь HR

**api/directors.py**

- `GET /directors/me` - получить информацию о своем складе (для директора)
- `POST /directors/me/stats` - обновить свою статистику (директор, сегодня только)
- `GET /directors/list` - список всех директоров (HR/суперпользователь)
- `GET /directors/{location_id}/stats` - получить статистику любой локации (HR/суперпользователь)
- `POST /directors/{location_id}/stats` - обновить статистику любой локации (HR сегодня, суперпользователь любой день)

**api/locations.py**

- `GET /locations/list` - список всех локаций
- `GET /locations/{location_id}/assignments` - получить owners для локации на день
- `POST /locations/{location_id}/assignments` - установить owners для локации на день

**api/employees.py**

- `GET /employees/list` - список сотрудников (с опциональной фильтрацией по локации и дате)
- `GET /employees/{employee_id}/assignment` - получить назначение сотрудника
- `POST /employees/{employee_id}/assignment` - установить директора для сотрудника
- `POST /employees/{employee_id}/terminate` - отметить сотрудника как уволенного

**api/owner.py**

- `GET /owners` - список всех директоров (теперь доступно любому авторизованному пользователю)
- `POST /owners` - создать нового директора (суперпользователь только)
- `DELETE /owners/{owner_id}` - удалить директора (суперпользователь только)

**api/utils.py**

- `is_hr(session, user_id)` - проверить, является ли пользователь HR
- `get_director_location(session, user_id)` - получить информацию о складе директора
- `is_director_of_location(session, user_id, location_id)` - проверить, является ли пользователь директором конкретного склада

**api/main_page.py**

- `GET /` - главная страница
- `GET /contacts` - контакты
- `GET /hr` - HR панель (с проверкой доступа)
- `GET /director` - страница директора (с проверкой доступа)

### Frontend (Статические файлы)

**templates/hr.html**
Структура:

- Header с навигацией
- Секция фильтров:
  - dateFilter (select date)
  - directorSelect (select director from list)
  - locationSelect (select location)
  - loadBtn (load data button)
- Навигационные вкладки (nav-tabs):
  - Stats tab
  - Owners tab
  - Employees tab
- Tab content:
  - Stats: форма с 5 числовыми полями + кнопка сохранения
  - Owners: список текущих + мультиселект для выбора + кнопка сохранения
  - Employees: таблица со строками (имя, селект owner, кнопка сохранить)
- Footer

**static/js/hr.js**
Основные функции:

- `loadDirectors()` - загружает список директоров с `/directors/list` и заполняет селект
- `loadLocations()` - загружает список локаций с `/locations/list`
- `loadAllOwners()` - загружает всех owners с `/owners` в `allOwners` объект
- `loadAll()` - главная функция загрузки данных для выбранной локации и даты:
  - Загружает owners для локации
  - Загружает сотрудников локации
  - Загружает статистику
  - Обновляет статус редактируемости
- `updateEditableStatus()` - включает/отключает редактирование в зависимости от даты
- `saveStats()` - сохраняет изменения статистики
- `saveOwners()` - сохраняет изменения назначений owners
- `saveEmployeeAssignment(employeeId)` - сохраняет назначение сотрудника

**templates/director.html**
Структура для директора:

- Header с названием своего склада
- Дата фильтр
- Форма со 5 полями статистики
- Предупреждение для прошедших дней
- Кнопка сохранения (отключена для прошедших дней)

**static/js/director.js**

- Загружает информацию директора с `/directors/me`
- При изменении даты загружает статистику с `/directors/me/stats?day=...`
- Отключает форму и кнопку для прошедших дней
- При сохранении отправляет POST на `/directors/me/stats?day=...`

### База данных

#### Таблицы

**warehouse_directors** (роль директора)

```python
id: int (primary key)
user_id: int (foreign key -> user.id)
location_id: int (foreign key -> locations.id)
created_at: datetime
```

**locations** (простой каталог локаций)

```python
id: int (primary key)
location_name: str
created_at: datetime
```

**location_days** (ежедневная запись локации)

```python
id: int (primary key)
location_id: int (foreign key -> locations.id)
day: date
finalized: bool (default False)
created_at: datetime
```

**location_day_owners** (связь many-to-many)

```python
location_day_id: int (foreign key -> location_days.id)
owner_id: int (foreign key -> owner.id)
primary key: (location_day_id, owner_id)
```

**location_day_stats** (ежедневная статистика)

```python
id: int (primary key)
location_day_id: int (foreign key -> location_days.id)
arrived_actual: int (default 0)
expected: int (default 0)
outsourcing: int (default 0)
overtime: int (default 0) - минуты
lunch: int (default 0) - минуты
```

**employees** (данные сотрудников)

```python
id: int (primary key)
name: str
is_active: bool (default True)
terminated_at: datetime (nullable)
created_at: datetime
```

**employee_days** (ежедневное назначение сотрудника)

```python
id: int (primary key)
employee_id: int (foreign key -> employees.id)
day: date
owner_id: int (foreign key -> owner.id)
finalized: bool (default False)
created_at: datetime
```

**hrs** (роль HR пользователя)

```python
id: int (primary key)
user_id: int (foreign key -> user.id)
created_at: datetime
```

## Поток данных

### Загрузка страницы HR

1. Пользователь переходит на `/hr`
2. Backend проверяет `is_hr(user_id)` - если false, возвращает 403
3. Возвращается `hr.html`
4. JavaScript загружает с `/directors/list` список директоров
5. JavaScript загружает с `/locations/list` список локаций
6. JavaScript загружает с `/owners` всех owners

### Выбор локации и загрузка данных

1. Пользователь выбирает директора, локацию и дату
2. Нажимает "Загрузить"
3. JavaScript вызывает:
   - `GET /locations/{location_id}/assignments?day=...` - owners
   - `GET /employees/list?day=...&location_id=...` - сотрудники
   - `GET /directors/{location_id}/stats?day=...` - статистика
4. Данные отображаются в соответствующих вкладках

### Сохранение изменений

#### Статистика

1. Заполняет 5 полей в форме
2. Нажимает "Сохранить" в вкладке Stats
3. POST на `/directors/{location_id}/stats?day=...` с телом JSON
4. Backend проверяет:
   - Является ли пользователь HR или суперпользователем
   - Если HR и день != сегодня - ошибка
   - Если суперпользователь - разрешить
5. Обновляет таблицу `location_day_stats`
6. Возвращает обновленные данные

#### Owners

1. В мультиселекте выбирает owners
2. Нажимает "Сохранить назначения" в вкладке Owners
3. POST на `/locations/{location_id}/assignments?day=...` с JSON `{owner_ids: [...]}`
4. Backend:
   - Проверяет доступ (HR/суперпользователь)
   - Удаляет старые связи в `location_day_owners`
   - Создаёт новые связи
5. Возвращает обновленный список

#### Employees

1. В таблице Employees выбирает owner в выпадающем списке
2. Нажимает "Сохранить" в этой строке
3. POST на `/employees/{employee_id}/assignment?day=...` с JSON `{owner_id: ...}`
4. Backend:
   - Проверяет доступ
   - Создаёт запись в `employee_days` для этой даты
   - Если уже существует - обновляет
5. Возвращает результат

## Безопасность

### Проверка доступа по ролям

```
GET /hr → check is_hr()
GET /director → check get_director_location()
POST /directors/{location_id}/stats → check is_hr() OR is_superuser
POST /employees/{employee_id}/assignment → check is_hr() OR is_superuser
```

### Ограничения по датам

```
if is_hr and selected_date < today and endpoint != GET:
    return 403 "Can only edit today"

if is_superuser:
    allow_any_date
```

### Защита от финализации

```
if location_day.finalized and not is_superuser:
    return 403 "Day is finalized"
```

## Миграция базы данных

Все таблицы добавлены через Alembic:

```bash
python -m alembic revision --autogenerate -m "Add new tables"
python -m alembic upgrade head
```

## Тестирование

### Ручное тестирование рекомендуется проверить:

1. ✅ HR пользователь может видеть и редактировать только текущий день
2. ✅ Суперпользователь может редактировать любой день
3. ✅ При выборе директора локации загружаются корректно
4. ✅ Мультиселект owners работает правильно
5. ✅ Сотрудники загружаются с правильной фильтрацией
6. ✅ Изменения сохраняются в БД
7. ✅ Прошедшие дни отключены для редактирования (для HR)
8. ✅ Суперпользователь может редактировать прошедшие дни

## Возможные расширения

1. **Пакетное редактирование** - позволить выбрать несколько дней сразу
2. **История изменений** - отслеживать кто и когда менял данные
3. **Экспорт отчётов** - скачивать статистику в Excel/PDF
4. **Аналитика** - графики и диаграммы по статистике
5. **Уведомления** - отправлять уведомления при изменении важных данных
6. **Финализация дня** - кнопка для закрытия дня (суперпользователь)
7. **Утверждение** - двухуровневое подтверждение для критических изменений
