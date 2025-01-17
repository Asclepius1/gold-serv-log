from typing import Optional
from pydantic import BaseModel

class OwnerBase(BaseModel):
    name: str

class OwnerUpdate(BaseModel):
    name: Optional[str]

class OwnerRead(OwnerBase):
    id: int

class OwnerCreate(OwnerBase):
    pass