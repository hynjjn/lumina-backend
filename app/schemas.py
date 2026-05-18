from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_guest: bool
    email: str | None
    name: str | None
    created_at: datetime


class AuthOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    user: UserOut


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt input limit
    name: str | None = Field(default=None, max_length=255)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class GoogleLoginOut(BaseModel):
    url: str


class RewriteIn(BaseModel):
    text: str = Field(min_length=1)
    level: int = Field(ge=1, le=5)


class RewriteOut(BaseModel):
    rewritten: str
    level: int


class ArticleIn(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    source_url: str | None = Field(default=None, max_length=2048)
    content: str = Field(min_length=1)


class ArticleImportIn(BaseModel):
    url: HttpUrl


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    source_url: str | None
    content: str
    created_at: datetime


class WordbookEntryIn(BaseModel):
    word: str = Field(min_length=1, max_length=128)
    context: str | None = None
    article_id: str | None = None
    definition_en: str | None = None
    definition_ko: str | None = None


class GlossIn(BaseModel):
    word: str = Field(min_length=1, max_length=128)
    context: str | None = Field(default=None, max_length=2000)


class GlossOut(BaseModel):
    word: str
    part_of_speech: str
    definitions_en: list[str]
    definition_ko: str
    examples: list[str]


class WordbookEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    word: str
    context: str | None
    article_id: str | None
    definition_en: str | None
    definition_ko: str | None
    image_url: str | None
    created_at: datetime
