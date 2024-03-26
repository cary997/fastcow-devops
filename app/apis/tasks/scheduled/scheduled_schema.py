from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column, JSON, DateTime


class PeriodicTaskBase(SQLModel):
    name: str = Field(max_length=200, unique=True)
    task: str = Field(max_length=200)
    args: list = Field(sa_type=JSON, default_factory=list)
    kwargs: dict = Field(
        sa_type=JSON, default_factory=dict, nullable=True
    )
    queue: Optional[str] = Field(max_length=200, nullable=True)
    exchange: Optional[str] = Field(max_length=200, nullable=True)
    routing_key: Optional[str] = Field(max_length=200, nullable=True)
    headers: Optional[dict] = Field(
        sa_type=JSON, default_factory=dict, nullable=True
    )
    priority: Optional[int] = Field(default=None, nullable=True)
    expires: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    expire_seconds: Optional[int] = Field(default=None, nullable=True)
    one_off: bool = Field(default=False)
    enabled: bool = Field(default=True)
    description: str = Field(max_length=200, nullable=True)
