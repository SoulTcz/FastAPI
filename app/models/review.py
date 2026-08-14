# app/models/review.py
# Ek user ek product pe sirf ek hi review de sakta hai (unique user_id + product_id combo -
# yeh check hum route ke andar karte hain, DB-level unique index bhi laga sakte ho baad me).

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class Review(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str            # current_user["email"]
    username: str           # review ke saath naam bhi store kar lete hain, dobara user lookup na karna pade
    product_id: str
    rating: int              # 1-5, validation schema me hoti hai
    comment: Optional[str] = None
    helpful_votes: int = 0
    unhelpful_votes: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
