# app/api/v1/cart.py
# Cart routes - sab logged-in user ke liye hain (Depends(get_current_user) har jagah).
# Ek user sirf apna khud ka cart dekh/badal sakta hai, doosre ka nahi.

from fastapi import APIRouter, Request, HTTPException, Depends
from typing import List
from bson import ObjectId

from app.schemas.cart_schema import CartItemAdd, CartItemUpdate, CartItemOut
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/cart", tags=["Cart"])


def _to_object_id(item_id: str) -> ObjectId:
    try:
        return ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


async def _get_product_or_404(request: Request, product_id: str) -> dict:
    """Helper: product dhoondta hai, active bhi hona chahiye - warna 404"""
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")

    product = await request.app.mongodb["products"].find_one({"_id": oid, "is_active": True})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/add", response_model=dict, status_code=201)
async def add_to_cart(item: CartItemAdd, request: Request,
                       current_user: dict = Depends(get_current_user)):
    """
    Cart me item add karta hai. Agar wahi product already cart me hai,
    to naya document nahi banata - quantity badha deta hai (real e-commerce jaisa behavior).
    """
    product = await _get_product_or_404(request, item.product_id)

    # Stock check - jitni quantity chahiye utni available honi chahiye
    if item.quantity > product["stock_quantity"]:
        raise HTTPException(
            status_code=400,
            detail=f"Only {product['stock_quantity']} units available in stock",
        )

    carts_collection = request.app.mongodb["carts"]

    existing_item = await carts_collection.find_one({
        "user_id": current_user["email"],
        "product_id": item.product_id,
    })

    if existing_item:
        # Already cart me hai - quantity badhao (total future stock ke against bhi check karo)
        new_quantity = existing_item["quantity"] + item.quantity
        if new_quantity > product["stock_quantity"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot add more. Only {product['stock_quantity']} units available in stock",
            )
        await carts_collection.update_one(
            {"_id": existing_item["_id"]},
            {"$set": {"quantity": new_quantity}},
        )
        return {"message": "Cart updated - quantity increased", "quantity": new_quantity}
    else:
        # Naya cart item banao
        from datetime import datetime
        await carts_collection.insert_one({
            "user_id": current_user["email"],
            "product_id": item.product_id,
            "quantity": item.quantity,
            "added_at": datetime.utcnow(),
        })
        return {"message": "Item added to cart", "quantity": item.quantity}


@router.get("", response_model=List[CartItemOut])
async def view_cart(request: Request, current_user: dict = Depends(get_current_user)):
    """Current user ka poora cart dikhata hai, product ke naam/price ke saath"""
    cart_items = await request.app.mongodb["carts"].find(
        {"user_id": current_user["email"]}
    ).to_list(None)

    result = []
    for item in cart_items:
        # Har cart-item ke liye uska product dhoondo (naam/price dikhane ke liye)
        try:
            product = await request.app.mongodb["products"].find_one(
                {"_id": ObjectId(item["product_id"])}
            )
        except Exception:
            product = None

        if product is None:
            continue  # product delete ho chuka ho to us item ko skip kar do

        result.append({
            "_id": str(item["_id"]),
            "product_id": item["product_id"],
            "product_name": product["name"],
            "product_price": product["price"],
            "quantity": item["quantity"],
            "subtotal": product["price"] * item["quantity"],
            "added_at": item["added_at"],
        })

    return result


@router.put("/update/{item_id}", response_model=dict)
async def update_cart_item(item_id: str, update: CartItemUpdate, request: Request,
                            current_user: dict = Depends(get_current_user)):
    """Cart item ki quantity update karta hai - sirf apne hi cart ka item update kar sakte ho"""
    oid = _to_object_id(item_id)

    cart_item = await request.app.mongodb["carts"].find_one(
        {"_id": oid, "user_id": current_user["email"]}   # ownership check yehi line hai
    )
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    product = await request.app.mongodb["products"].find_one(
        {"_id": ObjectId(cart_item["product_id"])}
    )
    if product and update.quantity > product["stock_quantity"]:
        raise HTTPException(
            status_code=400,
            detail=f"Only {product['stock_quantity']} units available in stock",
        )

    await request.app.mongodb["carts"].update_one(
        {"_id": oid}, {"$set": {"quantity": update.quantity}}
    )
    return {"message": "Cart item updated", "quantity": update.quantity}


@router.delete("/remove/{item_id}", response_model=dict)
async def remove_from_cart(item_id: str, request: Request,
                            current_user: dict = Depends(get_current_user)):
    """Cart se ek item hatata hai - sirf apna khud ka item hata sakte ho"""
    oid = _to_object_id(item_id)

    result = await request.app.mongodb["carts"].delete_one(
        {"_id": oid, "user_id": current_user["email"]}   # ownership check yaha bhi
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cart item not found")

    return {"message": "Item removed from cart"}
