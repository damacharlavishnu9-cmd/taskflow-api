"""Request and response models."""
from datetime import date, datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)


class Project(ProjectCreate):
    id: int
    owner_id: int | None
    created_at: datetime


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    priority: int = Field(default=3, ge=1, le=5)
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    priority: int | None = Field(default=None, ge=1, le=5)
    completed: bool | None = None
    due_date: date | None = None


class Task(BaseModel):
    id: int
    project_id: int
    title: str
    description: str
    priority: int
    completed: bool
    due_date: date | None
    created_at: datetime


class TaskPage(BaseModel):
    items: list[Task]
    total: int
    page: int
    page_size: int
    total_pages: int


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class Registration(Credentials):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class UserWithKey(BaseModel):
    id: int
    username: str
    api_key: str


class ProjectStats(BaseModel):
    total: int
    completed: int
    open: int
    overdue: int
    completion_rate: float
    by_priority: dict[str, int]


class ProjectSummary(ProjectStats):
    project_id: int
    name: str
