from pathlib import Path
from typing import List
from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from productmany.models import ProductDB, StoreDB
from productmany.schemas import (
    ProductCreate,
    ProductResponse,
    StoreCreate,
    StoreResponse,
    StoreWithProducts,
)
from .database import Base, get_db, engine
from jwt_app.auth import router as auth_router, get_current_user


Base.metadata.create_all(bind=engine)

app = FastAPI()

# exposes POST /login, issuing the same JWTs get_current_user below checks
app.include_router(auth_router)


@app.post("/products/", response_model=ProductResponse)
async def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    db_product = ProductDB(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@app.get("/products/", response_model=list[ProductResponse])
async def read_products(db: Session = Depends(get_db)):
    return db.query(ProductDB).all()

@app.get("/products/{product_id}", response_model=ProductResponse)
async def read_product(product_id: int, db: Session = Depends(get_db)):
    db_product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@app.delete("/products/{product_id}")
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
    return {"message": "Product deleted"}

@app.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    prod: ProductCreate,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    db_product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    db_product.name = prod.name
    db_product.category = prod.category
    db_product.price = prod.price

    db.commit()
    db.refresh(db_product)
    return db_product


# ============ create store =====
@app.post("/stores", response_model=StoreResponse)
async def create_store(
    store: StoreCreate,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    db_store = StoreDB(name=store.name)
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    return db_store

@app.get("/stores", response_model=List[StoreWithProducts])
async def read_stores(db: Session = Depends(get_db)):
    return db.query(StoreDB).all()

@app.delete("/stores/{store_id}")
async def delete_store(
    store_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    db_store = db.query(StoreDB).filter(StoreDB.id == store_id).first()
    if db_store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    db.delete(db_store)
    db.commit()
    return {"message": "Store deleted"}

@app.post("/products/{product_id}/stores/{store_id}")
async def sell_in_store(
    product_id: int,
    store_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    store = db.query(StoreDB).filter(StoreDB.id == store_id).first()

    if not product:
        return {"error": "Product not found"}
    if not store:
        return {"error": "Store not found"}

    if store not in product.stores:
        product.stores.append(store)
        db.commit()
    return {"message": "Now selling in this store"}

@app.delete("/products/{product_id}/stores/{store_id}")
async def stop_selling(
    product_id: int,
    store_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    store = db.query(StoreDB).filter(StoreDB.id == store_id).first()

    if not product:
        return {"error": "Product not found"}
    if not store:
        return {"error": "Store not found"}

    if store in product.stores:
        product.stores.remove(store)
        db.commit()
    return {"message": "Stopped selling in this store"}


# serve the frontend page (must be last so it doesn't shadow the API)
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="frontend")
