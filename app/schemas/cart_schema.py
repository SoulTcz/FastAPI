# app/schemas/cart_schema.py

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class CartItemAdd(BaseModel):
    """Cart me item add karte waqt client sirf yeh bhejega - user_id kabhi client se nahi lete,
    security ke liye wo hamesha token (current_user) se aata hai."""
    product_id: str
    quantity: int = 1

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v


class CartItemUpdate(BaseModel):
    """Quantity update karne ke liye"""
    quantity: int

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v


class CartItemOut(BaseModel):
    """Response me product ki basic details bhi dikhate hain, taaki client ko
    dobara /products/{id} call na karna pade har cart-item ke liye"""
    id: Optional[str] = Field(default=None, alias="_id")
    product_id: str
    product_name: str
    product_price: float
    quantity: int
    subtotal: float          # product_price * quantity
    added_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
