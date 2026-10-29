from pathlib import Path

from sqlalchemy import Column, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

sqlite_file_name = Path(__file__).parent / "products.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ProductDB(Base):
    __tablename__ = "products"
    # sqlite_autoincrement: SQLite never reuses an id, even after the last row is deleted
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(ProductDB).count() == 0:
            db.add_all([
                ProductDB(name="Iphone", price=143),
                ProductDB(name="Samsung", price=123),
                ProductDB(name="Nokia", price=100),
            ])
            db.commit()
    finally:
        db.close()
