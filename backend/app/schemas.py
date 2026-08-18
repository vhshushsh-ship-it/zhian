from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------- 认证 ----------
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str | None = None
    password: str = Field(..., min_length=6, max_length=72)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None = None
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- 笔记 ----------
class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = ""


class NoteUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = None


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
