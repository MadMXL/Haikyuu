from sqlalchemy import Column, Float, ForeignKey, Integer, String, Table
from .database import Base
from sqlalchemy.orm import relationship

product_stores = Table(
    'product_stores',
    Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id'), primary_key=True),
    Column('store_id', Integer, ForeignKey('stores.id'), primary_key=True)
)

class ProductDB(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True)
    category = Column(String, index=True)
    price = Column(Float, nullable=False)

    stores = relationship("StoreDB",
                secondary=product_stores,
                back_populates="products")

class StoreDB(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, index=True)

    products = relationship("ProductDB",
                secondary=product_stores,
                back_populates="stores")
