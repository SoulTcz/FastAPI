# app/schemas/order_schema.py

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from app.models.order import OrderStatus


class OrderCreate(BaseModel):
    """Order place karte waqt client sirf shipping address bhejega -
    items cart se aa jaate hain, client se items lena security risk hai
    (client price manipulate kar sakta hai)."""
    shipping_address: str

    @field_validator("shipping_address")
    @classmethod
    def address_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Shipping address cannot be empty")
        return v


class OrderItemOut(BaseModel):
    product_id: str
    product_name: str
    price: float
    quantity: int
    subtotal: float


class OrderOut(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    status: OrderStatus
    order_items: List[OrderItemOut]
    total_amount: float
    shipping_address: str
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class OrderStatusUpdate(BaseModel):
    """Admin order ka status update karne ke liye use karega"""
    status: OrderStatus


class OrderAnalyticsOut(BaseModel):
    """Admin analytics endpoint ka response"""
    total_orders: int
    total_sales: float
    orders_by_status: dict
