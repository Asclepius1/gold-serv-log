from fastapi_users import schemas


class UserRead(schemas.BaseUser[int]):
    name: str 
    owners_id: int|None

class UserCreate(schemas.BaseUserCreate):
    name: str 
    owners_id: int|None


class UserUpdate(schemas.BaseUserUpdate):
    name: str
    owners_id: int|None 
