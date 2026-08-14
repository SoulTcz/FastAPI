# app/api/v1/products.py
# PUBLIC routes hain - koi login/token nahi chahiye. Customer yaha se products browse karte hain.
# Sirf is_active=True products dikhte hain (admin ke "/admin/products" se yeh alag hai,
# jo inactive products bhi dikhata hai).

from fastapi import APIRouter, Request, HTTPException, Query
from typing import Optional
from bson import ObjectId

from app.schemas.product_schema import ProductOut

router = APIRouter(prefix="/api/v1/products", tags=["Public - Products"])


def _to_object_id(product_id: str) -> ObjectId:
    try:
        return ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")


@router.get("", response_model=dict)
async def list_products(
    request: Request,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),          # ge=1 -> page 1 se kam nahi ho sakta
    limit: int = Query(default=10, ge=1, le=100),  # le=100 -> ek baar me 100 se zyada items nahi
):
    """
    Products browse karne ka main endpoint. Sab filters optional hain.
    Example: /api/v1/products?category=Cakes&min_price=100&max_price=500&page=1&limit=10
    """
    # Filter dictionary dynamically banate hain - jo bhi query param diya gaya usi ke hisaab se
    filter_query: dict = {"is_active": True}

    if category:
        filter_query["category"] = category

    if min_price is not None or max_price is not None:
        price_filter = {}
        if min_price is not None:
            price_filter["$gte"] = min_price   # greater than or equal
        if max_price is not None:
            price_filter["$lte"] = max_price   # less than or equal
        filter_query["price"] = price_filter

    if search:
        # Naam YA description me match ho, dono me search karna hai isliye $or
        filter_query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},        # "i" = case-insensitive
            {"description": {"$regex": search, "$options": "i"}},
        ]

    # Total count nikalo (pagination info dikhane ke liye, pehle filter apply karke)
    total_count = await request.app.mongodb["products"].count_documents(filter_query)

    # Pagination: skip = kitne items chhodne hain pichle pages ke
    skip = (page - 1) * limit

    products_cursor = request.app.mongodb["products"].find(filter_query).skip(skip).limit(limit)
    products = await products_cursor.to_list(None)
    for p in products:
        p["_id"] = str(p["_id"])

    return {
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit,  # ceiling division
        "products": products,
    }


@router.get("/{product_id}", response_model=ProductOut)
async def get_product_details(product_id: str, request: Request):
    """Ek product ki poori detail - sirf active product dikhega, inactive nahi"""
    oid = _to_object_id(product_id)

    product = await request.app.mongodb["products"].find_one({"_id": oid, "is_active": True})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product["_id"] = str(product["_id"])
    return product
