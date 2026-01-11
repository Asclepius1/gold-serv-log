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

class EmployeeAssignmentUpdate(BaseModel):
    owner_id: Optional[int] = None
class ReportCreate(BaseModel):
    name: str
    param: str

class AccessChange(BaseModel):
    owner_id: int
    has_access: bool

class AccessChanges(BaseModel):
    access_changes: List[AccessChange]

class ErrorSchema(BaseModel):
    error_message: str
    color: str
    error_type: str