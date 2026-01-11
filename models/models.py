from datetime import datetime
from sqlalchemy import JSON, Date, DateTime, MetaData, Column, String, Integer, Table, Boolean, ForeignKey

metadata = MetaData()

owner = Table(
    "owners",
    metadata,
    Column("id", Integer, primary_key=True, index=True, autoincrement=True),
    Column("name", String, unique=True, index=True),
)

user = Table(
    "user",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String),
    Column("owners_id", Integer, ForeignKey(owner.c.id, ondelete='SET NULL'), nullable=True),
    Column("email", String),
    Column("hashed_password", String),
    Column("is_active", Boolean),
    Column("is_superuser", Boolean),
    Column("is_verified", Boolean),
    )

logs = Table(
    "logs",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("datetime", DateTime),
    Column("owner_name", String, index=True),
    Column("file_name", String),
    Column("message", String),
    Column("error_type", String, default='-', nullable=True),
    Column("color", String, default='green', nullable=True),
)

log_errors = Table(
    'log_errors',
    metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('error_message', String),
    Column('color', String, nullable=True),
    Column("error_type", String, default='-', nullable=True),

)

log_filters = Table(
    "log_filters",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("user_id", Integer, ForeignKey(user.c.id, ondelete="CASCADE"), nullable=True),
    Column("filters", JSON, nullable=True, default={})
)

files = Table(
    "files",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("owner_id", Integer, ForeignKey(owner.c.id, ondelete='SET NULL'), nullable=True),
    Column("filename", String),   
    Column("file_path", String),
    Column("created_at", DateTime, default=datetime.now),   
)

reports = Table(
    "reports",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("name", String),
    Column("param", String),

)

owner_report_access = Table(
    "owner_report_access",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("owner_id", Integer, ForeignKey(owner.c.id, ondelete='CASCADE')),  # ID пользователя
    Column("report_id", Integer, ForeignKey(reports.c.id, ondelete='CASCADE')),  # ID ссылки
    Column("is_disabled", Boolean, default=False),  # Флаг отключения ссылки для пользователя
)

locations = Table(
    "locations",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("location_name", String, unique=True, index=True),
    Column("created_at", DateTime, default=datetime.now),
    Column("is_active", Boolean, default=True),
)

# Таблица для хранения записи о смене (день) для каждой локации.
# Каждая запись привязывается к конкретной дате и флагу `finalized` —
# после установки которого изменения для этой локации и даты запрещены.
location_days = Table(
    "location_days",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("location_id", Integer, ForeignKey(locations.c.id, ondelete='CASCADE')),
    Column("day", Date, index=True),
    Column("finalized", Boolean, default=False),
    Column("created_at", DateTime, default=datetime.now),
)

# Таблица связи: какие owners назначены на конкретную локацию в конкретный день.
location_day_owners = Table(
    "location_day_owners",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("location_day_id", Integer, ForeignKey(location_days.c.id, ondelete='CASCADE')),
    Column("owner_id", Integer, ForeignKey(owner.c.id, ondelete='CASCADE')),
)

# Сотрудники: базовая информация и статус (уволен или нет).
employees = Table(
    "employees",
    metadata,
    Column("id", Integer, primary_key=True, index=True, autoincrement=True),
    Column("name", String, index=True),
    Column("is_active", Boolean, default=True),
    Column("terminated_at", DateTime, nullable=True),
    Column("created_at", DateTime, default=datetime.now),
)

# История привязки сотрудника к owner по дням. Одна запись = один день, один owner.
employee_days = Table(
    "employee_days",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("employee_id", Integer, ForeignKey(employees.c.id, ondelete='CASCADE')),
    Column("day", Date, index=True),
    Column("owner_id", Integer, ForeignKey(owner.c.id, ondelete='SET NULL'), nullable=True),
    Column("finalized", Boolean, default=False),
    Column("created_at", DateTime, default=datetime.now),
)

# Роль директор склада: привязка user -> location
warehouse_directors = Table(
    "warehouse_directors",
    metadata,
    Column("id", Integer, primary_key=True, index=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey(user.c.id, ondelete='CASCADE')),
    Column("location_id", Integer, ForeignKey(locations.c.id, ondelete='CASCADE')),
    Column("created_at", DateTime, default=datetime.now),
    Column("is_active", Boolean, default=True),
)

# История привязки директоров к складам по дням.
# Записывает, на каком складе был директор в каждый день.
warehouse_directors_history = Table(
    "warehouse_directors_history",
    metadata,
    Column("id", Integer, primary_key=True, index=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey(user.c.id, ondelete='CASCADE')),
    Column("location_id", Integer, ForeignKey(locations.c.id, ondelete='CASCADE')),
    Column("day", Date, index=True),
    Column("created_at", DateTime, default=datetime.now),
)

# Статистика по локации за день, управляемая директором склада
location_day_stats = Table(
    "location_day_stats",
    metadata,
    Column("id", Integer, primary_key=True, index=True, autoincrement=True),
    Column("location_day_id", Integer, ForeignKey(location_days.c.id, ondelete='CASCADE'), unique=True),
    Column("arrived_actual", Integer, default=0),
    Column("expected", Integer, default=0),
    Column("outsourcing", Integer, default=0),
    Column("overtime", Integer, default=0),
    Column("lunch", Integer, default=0),
    Column("created_at", DateTime, default=datetime.now),
)

# HR role mapping: which users are HRs
hrs = Table(
    "hrs",
    metadata,
    Column("id", Integer, primary_key=True, index=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey(user.c.id, ondelete='CASCADE')),
    Column("created_at", DateTime, default=datetime.now),
)