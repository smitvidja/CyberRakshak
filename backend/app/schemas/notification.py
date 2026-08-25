from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notification_type: str
    title: str
    message: str
    data: dict[str, object] | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime
