# app/models/cart.py
# Cart me har item apna alag document hai (ek user ke multiple cart-item documents ho sakte hain)

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CartItem(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str          # current_user["email"] yaha jaayega - kis user ka cart-item hai
    product_id: str       # kis product ka hai (string me store, ObjectId nahi - simplicity ke liye)
    quantity: int
    added_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
