# app/schemas/product_schema.py

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# ---------- Category ----------
class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None


class CategoryOut(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    description: Optional[str] = None

    class Config:
        populate_by_name = True


# ---------- Product ----------
class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    sku: str
    category: str
    stock_quantity: int = 0

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        return v

    @field_validator("stock_quantity")
    @classmethod
    def stock_cannot_be_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Stock quantity cannot be negative")
        return v


class ProductUpdate(BaseModel):
    """Sab fields optional hain - jo bhejoge wahi update hoga (exclude_unset=True use karenge)"""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    stock_quantity: Optional[int] = None
    is_active: Optional[bool] = None


class ProductOut(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    description: str
    price: float
    sku: str
    category: str
    stock_quantity: int
    images: List[str] = []
    is_active: bool
    average_rating: float = 0.0
    created_by: str
    created_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
