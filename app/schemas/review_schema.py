# app/schemas/review_schema.py

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ReviewCreate(BaseModel):
    rating: int
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def rating_must_be_1_to_5(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class ReviewUpdate(BaseModel):
    """Edit karte waqt dono optional - jo bhejoge wahi update hoga"""
    rating: Optional[int] = None
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def rating_must_be_1_to_5(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 5):
            raise ValueError("Rating must be between 1 and 5")
        return v


class ReviewOut(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    username: str
    product_id: str
    rating: int
    comment: Optional[str] = None
    helpful_votes: int = 0
    unhelpful_votes: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class ReviewVote(BaseModel):
    """helpful=True -> helpful_votes++, helpful=False -> unhelpful_votes++"""
    helpful: bool
