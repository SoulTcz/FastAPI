# app/api/v1/admin_product_images.py
# Admin product images upload/delete karta hai. Sirf admin access kar sakta hai.

from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File
from bson import ObjectId
import os

from app.core.security import get_current_admin_user
from app.core.file_utils import validate_image, save_uploaded_file
from app.core.config import UPLOAD_FOLDER

router = APIRouter(prefix="/api/v1/admin/products", tags=["Admin - Product Images"])


def _to_object_id(product_id: str) -> ObjectId:
    """URL se aaya string ID ko MongoDB ke ObjectId me convert karta hai, invalid ho to 400"""
    try:
        return ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")


@router.post("/{product_id}/images", response_model=dict, status_code=201)
async def upload_product_image(
    product_id: str,
    request: Request,
    file: UploadFile = File(...),
    admin: dict = Depends(get_current_admin_user),
):
    """
    Ek image upload karta hai, product ke 'images' array me path add karta hai.
    Zyada images add karni ho to isi endpoint ko dobara call karo, alag file ke saath -
    yeh purani images ko delete nahi karta, bas array me naya path jod deta hai.
    """
    oid = _to_object_id(product_id)

    # Pehle check karo product exist karta hai
    product = await request.app.mongodb["products"].find_one({"_id": oid})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # File validate karo
    is_valid = await validate_image(file)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file: {file.filename}. Only jpg/jpeg/png/webp allowed, max 5MB.",
        )

    # Disk pe save karo, unique naam ke saath
    saved_path = save_uploaded_file(file, UPLOAD_FOLDER)

    # Product document me naya image path array me jodo
    await request.app.mongodb["products"].update_one(
        {"_id": oid},
        {"$push": {"images": saved_path}},
    )

    updated_product = await request.app.mongodb["products"].find_one({"_id": oid})

    return {
        "message": "Image uploaded successfully",
        "images": updated_product["images"],
    }


@router.delete("/{product_id}/images", response_model=dict)
async def delete_product_image(
    product_id: str,
    image_path: str,
    request: Request,
    admin: dict = Depends(get_current_admin_user),
):
    """
    Ek image ko product se hataata hai (query param 'image_path' se) - DB se aur disk se dono.
    Example call: DELETE /api/v1/admin/products/{id}/images?image_path=uploads/xxxx.jpg
    """
    oid = _to_object_id(product_id)

    product = await request.app.mongodb["products"].find_one({"_id": oid})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if image_path not in product.get("images", []):
        raise HTTPException(status_code=404, detail="Image not found on this product")

    # DB se path hatao
    await request.app.mongodb["products"].update_one(
        {"_id": oid},
        {"$pull": {"images": image_path}},
    )

    # Disk se bhi file hatao (agar exist karti hai)
    if os.path.exists(image_path):
        os.remove(image_path)

    return {"message": "Image deleted successfully"}
