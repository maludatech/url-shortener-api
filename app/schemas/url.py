import uuid
from datetime import datetime

from pydantic import AnyUrl, BaseModel, ConfigDict


class ShortenRequest(BaseModel):
    long_url: AnyUrl


class ShortenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    short_code: str
    short_url: str
    long_url: str
    click_count: int
    created_at: datetime
