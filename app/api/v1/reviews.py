# app/api/v1/reviews.py
# Do routers is file me hain:
#   1. `product_reviews_router` -> /api/v1/products/{product_id}/reviews (add + list)
#   2. `reviews_router`         -> /api/v1/reviews/{review_id}          (edit/delete/vote)
# Alag isliye kyunki dusre wale routes me product_id path me nahi hota.

from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Request, HTTPException, Depends, Query

from app.core.security import get_current_user
from app.schemas.review_schema import ReviewCreate, ReviewUpdate, ReviewOut, ReviewVote

product_reviews_router = APIRouter(prefix="/api/v1/products", tags=["Reviews"])
reviews_router = APIRouter(prefix="/api/v1/reviews", tags=["Reviews"])


async def _recalculate_average_rating(request: Request, product_id: str) -> None:
    """Product ki saari reviews ka average nikal ke products collection me update karta hai.
    Har review add/edit/delete ke baad yeh call hota hai."""
    reviews_collection = request.app.mongodb["reviews"]

    cursor = reviews_collection.aggregate([
        {"$match": {"product_id": product_id}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}}},
    ])
    result = await cursor.to_list(None)
    new_average = round(result[0]["avg_rating"], 2) if result else 0.0

    try:
        product_oid = ObjectId(product_id)
    except Exception:
        return
    await request.app.mongodb["products"].update_one(
        {"_id": product_oid},
        {"$set": {"average_rating": new_average}},
    )


async def _has_purchased_product(request: Request, user_email: str, product_id: str) -> bool:
    """Business rule: sirf wahi user review de sakta hai jisne product order kiya AUR
    wo order 'delivered' ho chuka ho. Isse fake reviews rukte hain."""
    order = await request.app.mongodb["orders"].find_one({
        "user_id": user_email,
        "status": "delivered",
        "order_items.product_id": product_id,
    })
    return order is not None


def _to_object_id(review_id: str) -> ObjectId:
    try:
        return ObjectId(review_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid review id")


# ---------- Nested under /products/{product_id}/reviews ----------

@product_reviews_router.post("/{product_id}/reviews", response_model=ReviewOut, status_code=201)
async def add_review(product_id: str, review_data: ReviewCreate, request: Request,
                      current_user: dict = Depends(get_current_user)):
    """Review add karta hai - sirf ek baar per user per product, aur sirf purchase kiye hue product pe"""
    try:
        product_oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")

    product = await request.app.mongodb["products"].find_one({"_id": product_oid})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    reviews_collection = request.app.mongodb["reviews"]

    existing = await reviews_collection.find_one({
        "user_id": current_user["email"],
        "product_id": product_id,
    })
    if existing:
        raise HTTPException(status_code=400, detail="You have already reviewed this product")

    if not await _has_purchased_product(request, current_user["email"], product_id):
        raise HTTPException(
            status_code=403,
            detail="You can only review products you have purchased and received",
        )

    now = datetime.utcnow()
    review_doc = {
        "user_id": current_user["email"],
        "username": current_user["username"],
        "product_id": product_id,
        "rating": review_data.rating,
        "comment": review_data.comment,
        "helpful_votes": 0,
        "unhelpful_votes": 0,
        "created_at": now,
        "updated_at": now,
    }
    result = await reviews_collection.insert_one(review_doc)

    await _recalculate_average_rating(request, product_id)

    created = await reviews_collection.find_one({"_id": result.inserted_id})
    created["_id"] = str(created["_id"])
    return created


@product_reviews_router.get("/{product_id}/reviews", response_model=dict)
async def list_product_reviews(
    product_id: str,
    request: Request,
    sort_by: str = Query(default="newest", pattern="^(newest|oldest|highest_rating|lowest_rating|most_helpful)$"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
):
    """Product ki saari reviews - sorting aur pagination ke saath.
    sort_by: newest | oldest | highest_rating | lowest_rating | most_helpful"""
    reviews_collection = request.app.mongodb["reviews"]
    filter_query = {"product_id": product_id}

    sort_map = {
        "newest": ("created_at", -1),
        "oldest": ("created_at", 1),
        "highest_rating": ("rating", -1),
        "lowest_rating": ("rating", 1),
        "most_helpful": ("helpful_votes", -1),
    }
    sort_field, sort_direction = sort_map[sort_by]

    total_count = await reviews_collection.count_documents(filter_query)
    skip = (page - 1) * limit

    reviews = await reviews_collection.find(filter_query).sort(
        sort_field, sort_direction
    ).skip(skip).limit(limit).to_list(None)
    for r in reviews:
        r["_id"] = str(r["_id"])

    return {
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit,
        "reviews": reviews,
    }


# ---------- Standalone /reviews/{review_id} ----------

@reviews_router.put("/{review_id}", response_model=ReviewOut)
async def update_review(review_id: str, review_update: ReviewUpdate, request: Request,
                         current_user: dict = Depends(get_current_user)):
    """Sirf review ka author hi apni review edit kar sakta hai"""
    oid = _to_object_id(review_id)
    reviews_collection = request.app.mongodb["reviews"]

    review = await reviews_collection.find_one({"_id": oid, "user_id": current_user["email"]})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    update_data = review_update.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    update_data["updated_at"] = datetime.utcnow()
    await reviews_collection.update_one({"_id": oid}, {"$set": update_data})

    if "rating" in update_data:
        await _recalculate_average_rating(request, review["product_id"])

    updated = await reviews_collection.find_one({"_id": oid})
    updated["_id"] = str(updated["_id"])
    return updated


@reviews_router.delete("/{review_id}", response_model=dict)
async def delete_review(review_id: str, request: Request,
                         current_user: dict = Depends(get_current_user)):
    """Sirf review ka author hi apni review delete kar sakta hai (admin ke liye alag route hai)"""
    oid = _to_object_id(review_id)
    reviews_collection = request.app.mongodb["reviews"]

    review = await reviews_collection.find_one({"_id": oid, "user_id": current_user["email"]})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    await reviews_collection.delete_one({"_id": oid})
    await _recalculate_average_rating(request, review["product_id"])

    return {"message": "Review deleted successfully"}


@reviews_router.post("/{review_id}/vote", response_model=ReviewOut)
async def vote_review(review_id: str, vote: ReviewVote, request: Request,
                       current_user: dict = Depends(get_current_user)):
    """Helpful/unhelpful vote deta hai. Simplicity ke liye per-user vote-tracking nahi rakhi -
    (koi ek baar se zyada vote na kare, isके liye future me ek 'review_votes' collection banake
    user_id+review_id ka unique combo track karna behtar hoga)."""
    oid = _to_object_id(review_id)
    reviews_collection = request.app.mongodb["reviews"]

    review = await reviews_collection.find_one({"_id": oid})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    field_to_increment = "helpful_votes" if vote.helpful else "unhelpful_votes"
    await reviews_collection.update_one({"_id": oid}, {"$inc": {field_to_increment: 1}})

    updated = await reviews_collection.find_one({"_id": oid})
    updated["_id"] = str(updated["_id"])
    return updated
