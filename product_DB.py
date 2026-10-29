import os
import secrets
import time
import uuid
from contextlib import asynccontextmanager

import redis as redis_lib
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Float, ForeignKey, Integer, String, create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# login comes from jwt_app: same users, same JWT, same 5-wrong-tries lockout (stored in Redis)
from jwt_app.auth import get_current_user, router as auth_router
from jwt_app.db import Base as UserBase, engine as user_engine

UPLOAD_DIR = "upload"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# tests point this at a temp file so they never touch the real database.db
sqlite_file_name = os.getenv("PRODUCT_DB_FILE", "database.db")
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ProductDB(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    image = Column(String, nullable=True)
    # units still on sale: reserving takes units out, an unconfirmed reservation puts them back
    quantity = Column(Integer, nullable=False, default=0)


class ReservationDB(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    # wall-clock time (not monotonic) because it is stored in the database
    expires_at = Column(Float, nullable=False)
    # reserved -> confirmed (sold), or reserved -> expired/cancelled (amount rolled back)
    status = Column(String, nullable=False, default="reserved")


class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    quantity: int = Field(ge=0)


class ProductResponse(BaseModel):
    id: int
    name: str
    description: str
    price: float
    image: str | None = None
    quantity: int
    # available: quantity > 0, reserved: none left but some are on hold, sold: none left at all
    status: str

    model_config = ConfigDict(from_attributes=True)


class ReserveRequest(BaseModel):
    amount: int = Field(gt=0)


class Confirmation(BaseModel):
    reservation_token: str = Field(min_length=1, max_length=100)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # === startup ===
    print(f"[STARTUP] connecting SQLite ({sqlite_file_name})...")
    Base.metadata.create_all(bind=engine)
    UserBase.metadata.create_all(bind=user_engine)

    # create_all doesn't add columns to an existing table, so add new ones by hand
    new_columns = {
        "image": "VARCHAR",
        "quantity": "INTEGER NOT NULL DEFAULT 0",
    }
    existing = [c["name"] for c in inspect(engine).get_columns("products")]
    with engine.begin() as conn:
        for name, sql_type in new_columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE products ADD COLUMN {name} {sql_type}"))

    # fail fast if the database can't be reached
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    app.state.db_connected = True
    print("[STARTUP] database connected!")

    try:
        yield
    finally:
        # === shutdown ===
        engine.dispose()
        app.state.db_connected = False
        print("[SHUTDOWN] database connections closed")


app = FastAPI(lifespan=lifespan)

app.mount("/images", StaticFiles(directory=UPLOAD_DIR), name="images")

_redis = redis_lib.Redis(host="localhost", port=6379, decode_responses=True)
TOTAL_KEY = "products:total"
TOTAL_TTL = 60

RESERVATION_SECONDS = 30


def remove_image(filename: str | None):
    if filename and os.path.exists(f"{UPLOAD_DIR}/{filename}"):
        os.remove(f"{UPLOAD_DIR}/{filename}")


def give_back(db: Session, reservation: ReservationDB, new_status: str) -> bool:
    # flip the status only if it's still "reserved", so the amount is never returned twice
    flipped = (
        db.query(ReservationDB)
        .filter(ReservationDB.id == reservation.id, ReservationDB.status == "reserved")
        .update({ReservationDB.status: new_status})
    )
    if flipped:
        db.query(ProductDB).filter(ProductDB.id == reservation.product_id).update(
            {ProductDB.quantity: ProductDB.quantity + reservation.amount}
        )
    return bool(flipped)


def release_expired_reservations(db: Session):
    # purchase not confirmed in time: roll the product quantity back to what it was
    expired = (
        db.query(ReservationDB)
        .filter(ReservationDB.status == "reserved", ReservationDB.expires_at <= time.time())
        .all()
    )
    for reservation in expired:
        give_back(db, reservation, "expired")
    if expired:
        db.commit()


def with_status(db: Session, products: list[ProductDB]) -> list[ProductDB]:
    on_hold = {
        pid
        for (pid,) in db.query(ReservationDB.product_id)
        .filter(ReservationDB.status == "reserved")
        .distinct()
    }
    for p in products:
        if p.quantity > 0:
            p.status = "available"
        elif p.id in on_hold:
            p.status = "reserved"
        else:
            p.status = "sold"
    return products


def get_product_or_404(db: Session, product_id: int) -> ProductDB:
    db_product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)

app.include_router(auth_router)


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>CORS Demo</title>
    </head>
    <body>
        <h2>CORS HEAD Demo</h2>
        <p>HEAD is not in allow_methods — clicking the button triggers a CORS error.</p>
        <button onclick="callHeadFoo()">Call HEAD /foo</button>
        <pre id="head-output">waiting...</pre>
        <script>
            async function callHeadFoo() {
                const host = location.hostname === 'localhost' ? '127.0.0.1' : 'localhost';
                const url = location.protocol + '//' + host + ':' + location.port + '/foo';
                try {
                    const res = await fetch(url, {
                        method: 'HEAD',
                        headers: { 'X-Homework': 'cors-head' }
                    });
                    document.getElementById('head-output').innerText = "HEAD ok: status " + res.status;
                } catch (err) {
                    document.getElementById('head-output').innerText =
                        "CORS Error: " + err + "\\n(open DevTools > Console for full details)";
                }
            }
        </script>
    </body>
    </html>
    """


@app.head("/foo")
def head_foo():
    return {}


@app.get("/health")
async def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "online", "db_connected": app.state.db_connected}


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
    _redis.delete(TOTAL_KEY)
    return with_status(db, [db_product])[0]


@app.get("/products/total")
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


@app.get("/products/", response_model=list[ProductResponse])
async def read_products(
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    release_expired_reservations(db)
    return with_status(db, db.query(ProductDB).all())


@app.get("/products/{product_id}", response_model=ProductResponse)
async def read_product(
    product_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    release_expired_reservations(db)
    return with_status(db, [get_product_or_404(db, product_id)])[0]


@app.post("/products/{product_id}/reserve", status_code=201)
async def reserve_product(
    product_id: int,
    data: ReserveRequest,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    release_expired_reservations(db)
    db_product = get_product_or_404(db, product_id)

    # check and take the units in ONE statement, so two buyers can't both get the last ones
    taken = (
        db.query(ProductDB)
        .filter(ProductDB.id == product_id, ProductDB.quantity >= data.amount)
        .update({ProductDB.quantity: ProductDB.quantity - data.amount})
    )
    if not taken:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Not enough quantity: asked for {data.amount}, only {db_product.quantity} left",
        )

    token = secrets.token_urlsafe(24)
    db.add(
        ReservationDB(
            product_id=product_id,
            token=token,
            amount=data.amount,
            expires_at=time.time() + RESERVATION_SECONDS,
        )
    )
    db.commit()
    db.refresh(db_product)
    return {
        "message": f"Reserved {data.amount} for {RESERVATION_SECONDS} seconds",
        "reservation_token": token,
        "amount": data.amount,
        "expires_in": RESERVATION_SECONDS,
        "remaining_quantity": db_product.quantity,
    }


def get_reservation_or_error(db: Session, product_id: int, token: str) -> ReservationDB:
    reservation = (
        db.query(ReservationDB)
        .filter(ReservationDB.product_id == product_id, ReservationDB.token == token)
        .first()
    )
    if reservation is None:
        raise HTTPException(status_code=403, detail="Invalid reservation token")
    if reservation.status != "reserved":
        raise HTTPException(status_code=409, detail=f"Reservation already {reservation.status}")
    return reservation


@app.post("/products/{product_id}/confirm")
async def confirm_purchase(
    product_id: int,
    data: Confirmation,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    release_expired_reservations(db)
    reservation = get_reservation_or_error(db, product_id, data.reservation_token)
    # the units already left the product when reserving, so confirming only closes the reservation
    confirmed = (
        db.query(ReservationDB)
        .filter(ReservationDB.id == reservation.id, ReservationDB.status == "reserved")
        .update({ReservationDB.status: "confirmed"})
    )
    if not confirmed:
        raise HTTPException(status_code=409, detail="Reservation is no longer active")
    db.commit()
    return {"message": "Purchase confirmed", "product_id": product_id, "amount": reservation.amount}


@app.post("/products/{product_id}/cancel")
async def cancel_reservation(
    product_id: int,
    data: Confirmation,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    release_expired_reservations(db)
    reservation = get_reservation_or_error(db, product_id, data.reservation_token)
    if not give_back(db, reservation, "cancelled"):
        raise HTTPException(status_code=409, detail="Reservation is no longer active")
    db.commit()
    return {"message": "Reservation cancelled", "product_id": product_id, "amount": reservation.amount}


@app.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    db_product = get_product_or_404(db, product_id)
    remove_image(db_product.image)
    db.query(ReservationDB).filter(ReservationDB.product_id == product_id).delete()
    db.delete(db_product)
    db.commit()
    _redis.delete(TOTAL_KEY)
    return {"message": "Product deleted"}


@app.post("/products/{product_id}/image", response_model=ProductResponse)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    db_product = get_product_or_404(db, product_id)
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    name = f"{uuid.uuid4()}.{file.filename.split('.')[-1]}"
    with open(f"{UPLOAD_DIR}/{name}", "wb") as f:
        f.write(await file.read())
    remove_image(db_product.image)
    db_product.image = name
    db.commit()
    db.refresh(db_product)
    return with_status(db, [db_product])[0]


@app.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    prod: ProductCreate,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    db_product = get_product_or_404(db, product_id)
    for key, value in prod.model_dump().items():
        setattr(db_product, key, value)
    db.commit()
    db.refresh(db_product)
    return with_status(db, [db_product])[0]
