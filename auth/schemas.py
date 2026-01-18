from fastapi_users import schemas
from typing import Optional


class UserRead(schemas.BaseUser[int]):
    name: str 
    owners_id: int|None
    is_hr: bool = False

class UserCreate(schemas.BaseUserCreate):
    name: str 
    owners_id: int|None
    is_hr: bool = False


class UserUpdate(schemas.BaseUserUpdate):
    name: str
    owners_id: int|None
    is_hr: bool = False
