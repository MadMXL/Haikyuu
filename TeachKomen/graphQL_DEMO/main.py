from typing import List, Optional

import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter


app = FastAPI()

# @app.get("/")
# def root():
#     return{"hello, World"}

@strawberry.type
class Product:
    id: int
    name: str
    price: float

First_Product = Product(id=1, name="Iphone", price=67)

All_Product = [
    Product(id=1, name="Iphone", price=67),
    Product(id=2, name="IPAD", price=69420)
]


next_id = max(product.id for product in All_Product) + 1

@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello, World"
    @strawberry.field
    def foo(self) -> str:
        return "bar"

    @strawberry.field
    def product(self, id: int = 1) -> Optional[Product]:
        return next((product for product in All_Product if product.id == id), None)

    @strawberry.field
    def products(self, id: Optional[int] = None) -> List[Product]:
        if id is None:
            return All_Product
        return [product for product in All_Product if product.id == id]

@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_product(self, name: str, price: float) -> Product:
        global next_id
        new_product = Product(id=next_id, name=name, price=price)
        next_id += 1
        All_Product.append(new_product)
        return new_product
    
    @strawberry.mutation
    def update_product(self, id: int, name: Optional[str] = None, price: Optional[float] = None) -> Optional[Product]:
        product = next((product for product in All_Product if product.id == id), None)
        if product is None:
            return None
        if name is not None:
            product.name = name
        if price is not None:
            product.price = price
        return product
    
    @strawberry.mutation
    def delete_product(self, id: int) -> bool:
        product = next((product for product in All_Product if product.id == id), None)
        if product is None:
            return False
        All_Product.remove(product)
        return True

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)

app.include_router(graphql_app, prefix="/graphql")