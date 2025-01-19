from datetime import datetime
from sqlalchemy import JSON, DateTime, MetaData, Column, String, Integer, Table, Boolean, ForeignKey

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