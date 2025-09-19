from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List

class CreateJobRequest(BaseModel):
    config: Dict[str, Any]
    depth: Optional[int] = None
    max_pages: Optional[int] = None

class JobDTO(BaseModel):
    id: int
    status: str
    created_at: str
    updated_at: str
    depth: Optional[int] = None
    max_pages: Optional[int] = None

class EventDTO(BaseModel):
    id: int
    job_id: int
    type: str
    payload: Dict[str, Any]
    ts: str

class ItemRow(BaseModel):
    id: int
    page_id: int
    job_id: Optional[int]
    data_json: Dict[str, Any]
    created_at: str
