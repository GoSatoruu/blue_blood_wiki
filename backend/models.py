"""
models.py — Pydantic data models for Blue Blood Wiki articles.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class ArticleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300, description="Human-readable article title")
    slug: str = Field(..., min_length=1, max_length=200, description="URL-safe unique identifier")
    content: str = Field(default="", description="Raw Markdown source content")
    tags: str = Field(default="", description="Comma-separated list of tags")
    category: str = Field(default="General", max_length=100, description="Article category")

    @field_validator("slug")
    @classmethod
    def slug_must_be_safe(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError("Slug must be lowercase alphanumeric with hyphens only")
        return v

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, v: str) -> str:
        tags = [t.strip().lower() for t in v.split(",") if t.strip()]
        return ",".join(tags)


class ArticleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    content: Optional[str] = None
    tags: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        tags = [t.strip().lower() for t in v.split(",") if t.strip()]
        return ",".join(tags)


class ArticleOut(BaseModel):
    id: int
    slug: str
    title: str
    content: str
    html_content: str
    tags: str
    category: str
    view_count: int
    created_at: str
    updated_at: str

    @property
    def tag_list(self) -> list[str]:
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def created_dt(self) -> datetime:
        return datetime.fromisoformat(self.created_at)

    @property
    def updated_dt(self) -> datetime:
        return datetime.fromisoformat(self.updated_at)

    model_config = {"from_attributes": True}


class SearchResult(BaseModel):
    slug: str
    title: str
    tags: str
    category: str
    snippet: str = ""

    model_config = {"from_attributes": True}


class CategoryInfo(BaseModel):
    category: str
    article_count: int
