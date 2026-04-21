from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RoleCreate(BaseModel):
    name: str
    is_active: Optional[bool] = True
    created_by: Optional[str] = None

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = True
    updated_by: Optional[str] = None

class Role(BaseModel):
    id: str
    name: str
    is_active: bool
    created_at: datetime
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None