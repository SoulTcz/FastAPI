# app/api/v1/admin_products.py
# Yeh saare routes sirf admin access kar sakta hai - get_current_admin_user dependency
# check karti hai ki logged-in user "is_admin: true" hai ya nahi.

from fastapi import APIRouter, Request, HTTPException, Depends
from typing import List
from datetime import datetime

from app.schemas.product_schema import (
    ProductCreate, ProductUpdate, ProductOut, CategoryCreate, CategoryOut
)
from app.core.security import get_current_admin_user

router = APIRouter(prefix="/api/v1/admin", tags=["Admin - Products"])


# ---------- Category management ----------
@router.post("/categories", response_model=CategoryOut, status_code=201)
async def create_category(category: CategoryCreate, request: Request,
                           admin: dict = Depends(get_current_admin_user)):
    existing = await request.app.mongodb["categories"].find_one({"name": category.name})
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")

    result = await request.app.mongodb["categories"].insert_one(category.dict())
    created = await request.app.mongodb["categories"].find_one({"_id": result.inserted_id})
    created["_id"] = str(created["_id"])
    return created


@router.get("/categories", response_model=List[CategoryOut])
async def list_categories(request: Request, admin: dict = Depends(get_current_admin_user)):
    categories = await request.app.mongodb["categories"].find().to_list(None)
    for c in categories:
        c["_id"] = str(c["_id"])
    return categories


# ---------- Product CRUD (admin) ----------
@router.post("/products", response_model=ProductOut, status_code=201)
async def create_product(product: ProductCreate, request: Request,
                          admin: dict = Depends(get_current_admin_user)):
    # SKU unique hona chahiye
    existing = await request.app.mongodb["products"].find_one({"sku": product.sku})
    if existing:
        raise HTTPException(status_code=400, detail="A product with this SKU already exists")

    product_dict = product.dict()
    product_dict.update({
        "images": [],
        "is_active": True,
        "average_rating": 0.0,
        "created_by": admin["email"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })

    result = await request.app.mongodb["products"].insert_one(product_dict)
    created = await request.app.mongodb["products"].find_one({"_id": result.inserted_id})
    created["_id"] = str(created["_id"])
    return created


@router.get("/products", response_model=List[ProductOut])
async def list_all_products(request: Request, admin: dict = Depends(get_current_admin_user)):
    """Admin ko active + inactive dono products dikhte hain"""
    products = await request.app.mongodb["products"].find().to_list(None)
    for p in products:
        p["_id"] = str(p["_id"])
    return products


@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product_admin(product_id: str, request: Request,
                             admin: dict = Depends(get_current_admin_user)):
    from bson import ObjectId
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")

    product = await request.app.mongodb["products"].find_one({"_id": oid})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product["_id"] = str(product["_id"])
    return product


@router.put("/products/{product_id}", response_model=ProductOut)
async def update_product(product_id: str, product_update: ProductUpdate, request: Request,
                          admin: dict = Depends(get_current_admin_user)):
    from bson import ObjectId
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")

    update_data = product_update.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    result = await request.app.mongodb["products"].update_one({"_id": oid}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")

    updated = await request.app.mongodb["products"].find_one({"_id": oid})
    updated["_id"] = str(updated["_id"])
    return updated


@router.delete("/products/{product_id}", response_model=dict)
async def delete_product(product_id: str, request: Request,
                          admin: dict = Depends(get_current_admin_user)):
    from bson import ObjectId
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")

    result = await request.app.mongodb["products"].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}
