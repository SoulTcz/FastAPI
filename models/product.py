# app/models/product.py
# Product aur Category ke DB models (MongoDB me jaise store hote hain)

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class Category(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class Product(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    description: str
    price: float
    sku: str                              # unique product code, e.g. "CAKE-001"
    category: str                          # category name (ya category_id, simplicity ke liye name)
    stock_quantity: int = 0
    images: List[str] = []                 # image file paths, Week 4 me fill honge
    is_active: bool = True
    average_rating: float = 0.0            # Week 7 me use hoga
    created_by: str                        # admin ka user id/email jisne product banaya
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
