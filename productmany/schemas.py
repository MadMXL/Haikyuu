from pydantic import BaseModel

# smaller data first cuz the big one dont have key for the small one yet


class Store(BaseModel):
    name: str

class StoreCreate(Store):
    pass

class StoreResponse(Store):
    id: int
    class Config:
        from_attributes = True

# ======= Product ======
class Product(BaseModel):
    name: str
    category: str
    price: float

# in
class ProductCreate(Product):
    pass

# out
class ProductResponse(Product):
    id: int
    stores: list[StoreResponse]

    class Config:
        from_attributes = True

# product without its stores, used inside StoreWithProducts to avoid infinite nesting
class ProductBrief(Product):
    id: int
    class Config:
        from_attributes = True

# store WITH the products it sells, used by GET /stores
class StoreWithProducts(Store):
    id: int
    products: list[ProductBrief]

    class Config:
        from_attributes = True
