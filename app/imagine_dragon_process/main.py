from fastapi import FastAPI

from keras1 import router as keras1_router

app = FastAPI()

app.include_router(keras1_router)