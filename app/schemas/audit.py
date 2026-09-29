from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: Optional[str] = None
    action: str = Field(
        ..., description="Action performed, e.g. CLAIM_VERIFIED, DOCUMENT_UPLOADED"
    )
    entity_type: str = Field(
        ..., description="Type of entity, e.g. loan, document, claim"
    )
    entity_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: List[AuditLogEntry]
    total: int
