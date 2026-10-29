import redis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import get_current_user
from .db import get_db, ProductDB

router = APIRouter()

_redis = redis.Redis(host="localhost", port=6379, decode_responses=True)
TOTAL_KEY = "products:total"
TOTAL_TTL = 60  # seconds


class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    price: float


@router.post("/products", status_code=201)
async def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    db_product = ProductDB(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    _redis.delete(TOTAL_KEY)
    return db_product


@router.get("/products/total")
async def get_products_total(
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    cached = _redis.get(TOTAL_KEY)
    if cached is not None:
        return {"total": int(cached), "source": "cache"}
    total = db.query(ProductDB).count()
    _redis.setex(TOTAL_KEY, TOTAL_TTL, total)
    return {"total": total, "source": "db"}


@router.get("/products")
async def read_products(
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    return db.query(ProductDB).all()


@router.get("/products/{product_id}")
async def read_product(
    product_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    db_product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@router.put("/products/{product_id}")
async def update_product(
    product_id: int,
    product: ProductCreate,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    db_product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    db_product.name = product.name
    db_product.description = product.description
    db_product.price = product.price
    db.commit()
    db.refresh(db_product)
    return db_product


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    db_product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(db_product)
    db.commit()
    _redis.delete(TOTAL_KEY)
    return {"message": "Product deleted"}
