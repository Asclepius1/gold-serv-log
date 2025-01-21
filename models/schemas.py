from typing import List, Optional
from pydantic import BaseModel

class OwnerBase(BaseModel):
    name: str

class OwnerUpdate(BaseModel):
    name: Optional[str]

class OwnerRead(OwnerBase):
    id: int

class OwnerCreate(OwnerBase):
    pass

class ReportCreate(BaseModel):
    name: str
    param: str

class AccessChange(BaseModel):
    owner_id: int
    has_access: bool

class AccessChanges(BaseModel):
    access_changes: List[AccessChange]