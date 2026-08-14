# app/api/v1/orders.py
# Customer-facing order routes. Ek user sirf apne khud ke orders dekh/cancel kar sakta hai.
# Order hamesha current cart se banta hai - client seedha items nahi bhej sakta (security).

from datetime import datetime
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Request, HTTPException, Depends

from app.core.security import get_current_user
from app.models.order import OrderStatus
from app.schemas.order_schema import OrderCreate, OrderOut

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])

# Order place hone ke baad in statuses tak hi cancel allowed hai.
# Ek baar "shipped" ho gaya to customer khud cancel nahi kar sakta.
CANCELLABLE_STATUSES = {OrderStatus.pending, OrderStatus.confirmed}


def _to_object_id(order_id: str) -> ObjectId:
    try:
        return ObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order id")


@router.post("", response_model=OrderOut, status_code=201)
async def place_order(order_data: OrderCreate, request: Request,
                       current_user: dict = Depends(get_current_user)):
    """
    Cart se order banata hai:
    1. Cart empty nahi honi chahiye
    2. Har item ka stock available hona chahiye (sab check hone ke baad hi kuch update karte hain,
       taaki koi partial/half-order na bane)
    3. Stock reduce hota hai
    4. Order document banta hai (price/name ka snapshot le liya jaata hai)
    5. Cart clear ho jaata hai
    """
    carts_collection = request.app.mongodb["carts"]
    products_collection = request.app.mongodb["products"]
    orders_collection = request.app.mongodb["orders"]

    cart_items = await carts_collection.find({"user_id": current_user["email"]}).to_list(None)
    if not cart_items:
        raise HTTPException(status_code=400, detail="Your cart is empty")

    # ---------- Pass 1: sab kuch validate karo, kuch bhi update mat karo ----------
    order_items = []
    total_amount = 0.0
    products_to_reduce = []  # (product_oid, quantity) - baad me stock reduce karne ke liye

    for item in cart_items:
        try:
            product_oid = ObjectId(item["product_id"])
        except Exception:
            continue  # corrupted cart item, skip

        product = await products_collection.find_one({"_id": product_oid, "is_active": True})
        if not product:
            raise HTTPException(
                status_code=400,
                detail=f"A product in your cart is no longer available. Please remove it from cart.",
            )

        if item["quantity"] > product["stock_quantity"]:
            raise HTTPException(
                status_code=400,
                detail=f"'{product['name']}' has only {product['stock_quantity']} units in stock",
            )

        subtotal = product["price"] * item["quantity"]
        order_items.append({
            "product_id": str(product["_id"]),
            "product_name": product["name"],
            "price": product["price"],
            "quantity": item["quantity"],
            "subtotal": subtotal,
        })
        total_amount += subtotal
        products_to_reduce.append((product_oid, item["quantity"]))

    # ---------- Pass 2: ab sab validate ho chuka, safely update karo ----------
    for product_oid, quantity in products_to_reduce:
        await products_collection.update_one(
            {"_id": product_oid},
            {"$inc": {"stock_quantity": -quantity}},
        )

    now = datetime.utcnow()
    order_doc = {
        "user_id": current_user["email"],
        "status": OrderStatus.pending.value,
        "order_items": order_items,
        "total_amount": round(total_amount, 2),
        "shipping_address": order_data.shipping_address,
        "created_at": now,
        "updated_at": now,
    }
    result = await orders_collection.insert_one(order_doc)

    # Order ban gaya, ab cart clear kar do
    await carts_collection.delete_many({"user_id": current_user["email"]})

    created = await orders_collection.find_one({"_id": result.inserted_id})
    created["_id"] = str(created["_id"])
    return created


@router.get("", response_model=List[OrderOut])
async def list_my_orders(request: Request, current_user: dict = Depends(get_current_user)):
    """Current user ki order history - newest pehle"""
    orders = await request.app.mongodb["orders"].find(
        {"user_id": current_user["email"]}
    ).sort("created_at", -1).to_list(None)

    for o in orders:
        o["_id"] = str(o["_id"])
    return orders


@router.get("/{order_id}", response_model=OrderOut)
async def get_order_details(order_id: str, request: Request,
                             current_user: dict = Depends(get_current_user)):
    """Ek specific order ki detail - sirf apna khud ka order dekh sakte ho"""
    oid = _to_object_id(order_id)

    order = await request.app.mongodb["orders"].find_one(
        {"_id": oid, "user_id": current_user["email"]}   # ownership check
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order["_id"] = str(order["_id"])
    return order


@router.put("/{order_id}/cancel", response_model=OrderOut)
async def cancel_order(order_id: str, request: Request,
                        current_user: dict = Depends(get_current_user)):
    """
    Order cancel karta hai, agar status abhi cancellable hai (pending/confirmed).
    Cancel hone par stock wapas add kar dete hain (restock).
    """
    oid = _to_object_id(order_id)
    orders_collection = request.app.mongodb["orders"]

    order = await orders_collection.find_one({"_id": oid, "user_id": current_user["email"]})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order["status"] not in {s.value for s in CANCELLABLE_STATUSES}:
        raise HTTPException(
            status_code=400,
            detail=f"Order with status '{order['status']}' cannot be cancelled",
        )

    # Stock restore karo - jitna order me tha utna wapas add kar do
    products_collection = request.app.mongodb["products"]
    for item in order["order_items"]:
        try:
            product_oid = ObjectId(item["product_id"])
        except Exception:
            continue
        await products_collection.update_one(
            {"_id": product_oid},
            {"$inc": {"stock_quantity": item["quantity"]}},
        )

    await orders_collection.update_one(
        {"_id": oid},
        {"$set": {"status": OrderStatus.cancelled.value, "updated_at": datetime.utcnow()}},
    )

    updated = await orders_collection.find_one({"_id": oid})
    updated["_id"] = str(updated["_id"])
    return updated
