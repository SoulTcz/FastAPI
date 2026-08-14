# app/models/order.py
# Order ek "snapshot" hai - jo cart me tha wo yaha copy ho jaata hai (price, name waqt-e-order).
# Isliye agar baad me product ka price/naam change ho jaaye, purane orders unaffected rehte hain.

from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    """str, Enum -> Mongo me plain string ki tarah store hoga (e.g. \"pending\")"""
    pending = "pending"
    confirmed = "confirmed"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


class OrderItem(BaseModel):
    """Order ke andar embedded hota hai - alag collection nahi banate (order ke saath hi read hota hai)"""
    product_id: str
    product_name: str
    price: float          # order place hote waqt ka price (snapshot)
    quantity: int
    subtotal: float        # price * quantity

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Order(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str                              # current_user["email"]
    status: OrderStatus = OrderStatus.pending
    order_items: List[OrderItem]
    total_amount: float
    shipping_address: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
