from typing import List

import strawberry

from database import ProductDB, SessionLocal


@strawberry.type
class Product:
    id: int
    name: str
    price: float

    @classmethod
    def from_db(cls, product: ProductDB) -> "Product":
        return cls(
            id=product.id,
            name=product.name,
            price=product.price
        )


@strawberry.input
class ProductInput:
    name: str
    price: float


@strawberry.input
class ProductUpdateInput:
    name: str | None = None
    price: float | None = None


@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello, World!"

    @strawberry.field
    def product(self, id: int) -> Product | None:
        with SessionLocal() as db:
            p = db.get(ProductDB, id)
            return Product.from_db(p) if p else None

    @strawberry.field
    def products(self) -> List[Product]:
        with SessionLocal() as db:
            return [Product.from_db(p) for p in db.query(ProductDB).order_by(ProductDB.id)]


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_product(self, input: ProductInput) -> Product:
 
        with SessionLocal() as db:
            p = ProductDB(name=input.name, price=input.price)
            db.add(p)
            db.commit()
            db.refresh(p)
            return Product.from_db(p)

    @strawberry.mutation
    def update_product(self, id: int, input: ProductUpdateInput) -> Product | None:
        with SessionLocal() as db:
            p = db.get(ProductDB, id)
            if p is None:
                return None
            if input.name is not None:
                p.name = input.name
            if input.price is not None:
                p.price = input.price
            db.commit()
            db.refresh(p)
            return Product.from_db(p)

    @strawberry.mutation
    def delete_product(self, id: int) -> bool:
        with SessionLocal() as db:
            p = db.get(ProductDB, id)
            if p is None:
                return False
            db.delete(p)
            db.commit()
            return True


schema = strawberry.Schema(query=Query, mutation=Mutation)
