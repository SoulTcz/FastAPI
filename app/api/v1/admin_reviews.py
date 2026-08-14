# app/api/v1/admin_reviews.py
# Admin moderation - saari reviews dekh sakta hai, koi bhi inappropriate review delete kar sakta hai
# (author ka wait nahi karna padta).

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from typing import Optional
from bson import ObjectId

from app.core.security import get_current_admin_user

router = APIRouter(prefix="/api/v1/admin/reviews", tags=["Admin - Reviews"])


@router.get("", response_model=dict)
async def list_all_reviews(
    request: Request,
    product_id: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    admin: dict = Depends(get_current_admin_user),
):
    """Moderation ke liye saari reviews - optionally ek product ke liye filter kar sakte ho"""
    reviews_collection = request.app.mongodb["reviews"]
    filter_query = {}
    if product_id:
        filter_query["product_id"] = product_id

    total_count = await reviews_collection.count_documents(filter_query)
    skip = (page - 1) * limit

    reviews = await reviews_collection.find(filter_query).sort(
        "created_at", -1
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


@router.delete("/{review_id}", response_model=dict)
async def moderate_delete_review(review_id: str, request: Request,
                                  admin: dict = Depends(get_current_admin_user)):
    """Admin kisi bhi review ko delete kar sakta hai (author check nahi hota yaha)"""
    try:
        oid = ObjectId(review_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid review id")

    reviews_collection = request.app.mongodb["reviews"]
    review = await reviews_collection.find_one({"_id": oid})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    await reviews_collection.delete_one({"_id": oid})

    # Rating dobara calculate karo kyunki ek review hat gayi
    from app.api.v1.reviews import _recalculate_average_rating
    await _recalculate_average_rating(request, review["product_id"])

    return {"message": "Review removed by admin"}
