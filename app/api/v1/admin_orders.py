# app/api/v1/admin_orders.py
# Admin-only order management - saare orders dekh sakta hai, status update kar sakta hai.

from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Request, HTTPException, Depends, Query

from app.core.security import get_current_admin_user
from app.models.order import OrderStatus
from app.schemas.order_schema import OrderOut, OrderStatusUpdate, OrderAnalyticsOut

router = APIRouter(prefix="/api/v1/admin/orders", tags=["Admin - Orders"])


@router.get("", response_model=dict)
async def list_all_orders(
    request: Request,
    status: Optional[OrderStatus] = None,
    customer_email: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    admin: dict = Depends(get_current_admin_user),
):
    """
    Saare orders, filter aur pagination ke saath.
    Example: /api/v1/admin/orders?status=pending&customer_email=abc@x.com&page=1&limit=10
    """
    filter_query: dict = {}

    if status:
        filter_query["status"] = status.value

    if customer_email:
        filter_query["user_id"] = customer_email

    if start_date is not None or end_date is not None:
        date_filter = {}
        if start_date is not None:
            date_filter["$gte"] = start_date
        if end_date is not None:
            date_filter["$lte"] = end_date
        filter_query["created_at"] = date_filter

    orders_collection = request.app.mongodb["orders"]
    total_count = await orders_collection.count_documents(filter_query)

    skip = (page - 1) * limit
    orders = await orders_collection.find(filter_query).sort(
        "created_at", -1
    ).skip(skip).limit(limit).to_list(None)

    for o in orders:
        o["_id"] = str(o["_id"])

    return {
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit,
        "orders": orders,
    }


@router.get("/analytics/summary", response_model=OrderAnalyticsOut)
async def order_analytics(request: Request, admin: dict = Depends(get_current_admin_user)):
    """Basic sales analytics - total orders, total sales (cancelled ko total_sales me nahi ginte),
    aur status ke hisaab se breakdown"""
    orders_collection = request.app.mongodb["orders"]

    total_orders = await orders_collection.count_documents({})

    # Cancelled orders ko revenue me count nahi karte
    sales_cursor = orders_collection.aggregate([
        {"$match": {"status": {"$ne": OrderStatus.cancelled.value}}},
        {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}},
    ])
    sales_result = await sales_cursor.to_list(None)
    total_sales = sales_result[0]["total"] if sales_result else 0.0

    status_cursor = orders_collection.aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ])
    status_result = await status_cursor.to_list(None)
    orders_by_status = {row["_id"]: row["count"] for row in status_result}

    return {
        "total_orders": total_orders,
        "total_sales": round(total_sales, 2),
        "orders_by_status": orders_by_status,
    }


@router.get("/{order_id}", response_model=OrderOut)
async def get_order_admin(order_id: str, request: Request,
                           admin: dict = Depends(get_current_admin_user)):
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order id")

    order = await request.app.mongodb["orders"].find_one({"_id": oid})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order["_id"] = str(order["_id"])
    return order


@router.put("/{order_id}/status", response_model=OrderOut)
async def update_order_status(order_id: str, status_update: OrderStatusUpdate, request: Request,
                               admin: dict = Depends(get_current_admin_user)):
    """Admin order ka status badalta hai (pending -> confirmed -> shipped -> delivered),
    ya cancel bhi kar sakta hai. Agar admin khud cancel karta hai to stock bhi restore ho jaata hai."""
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order id")

    orders_collection = request.app.mongodb["orders"]
    order = await orders_collection.find_one({"_id": oid})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order["status"] == OrderStatus.cancelled.value:
        raise HTTPException(status_code=400, detail="A cancelled order's status cannot be changed")

    # Agar admin ab isko cancel kar raha hai aur pehle cancelled nahi tha, stock restore karo
    if status_update.status == OrderStatus.cancelled and order["status"] != OrderStatus.cancelled.value:
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
        {"$set": {"status": status_update.status.value, "updated_at": datetime.utcnow()}},
    )

    updated = await orders_collection.find_one({"_id": oid})
    updated["_id"] = str(updated["_id"])
    return updated
