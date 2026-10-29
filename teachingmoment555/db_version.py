# STEP 6 — same lesson with a real database (see README.md)
#
# Run from the folder ABOVE teachingmoment555:
#        uvicorn teachingmoment555.db_version:app --reload --port 8005
# Test:  curl.exe http://127.0.0.1:8005/products-normal
#        curl.exe -N http://127.0.0.1:8005/products-stream

from fastapi import FastAPI, Depends  # same tools as before, plus Depends to hand each request a db session
from fastapi.responses import StreamingResponse
from sqlalchemy import Column, Integer, String, Float, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

engine = create_engine("sqlite:///./teachingmoment555/shop.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)  # makes a new db conversation each request
Base = declarative_base()


class Product(Base):  # one row of this = one product in the database
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Float)


Base.metadata.create_all(bind=engine)  # creates the products table if it doesn't exist yet

app = FastAPI()


def get_db():  # opens a db session for one request, always closes it after
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def seed():  # put 10 fake products in the table so there's something to query
    db = SessionLocal()
    if db.query(Product).count() == 0:
        for i in range(1, 11):
            db.add(Product(name=f"Product {i}", price=9.99 + i))
        db.commit()
    db.close()


@app.get("/products-normal")  # the normal way: query all rows, then return them all at once
def products_normal(db: Session = Depends(get_db)):
    products = db.query(Product).all()  # every row is now sitting in memory
    return [{"id": p.id, "name": p.name, "price": p.price} for p in products]  # nothing sent until this line


@app.get("/products-stream")  # the streaming way: same query, one row sent at a time
def products_stream(db: Session = Depends(get_db)):
    def generate():
        for p in db.query(Product):  # loop over the query results one by one
            yield f"{p.id},{p.name},{p.price}\n"  # send this row immediately

    return StreamingResponse(generate(), media_type="text/plain")
