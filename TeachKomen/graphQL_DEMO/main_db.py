from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from strawberry.fastapi import GraphQLRouter

from database import init_db
from schema import schema

app = FastAPI()

init_db()

graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

# Web frontend at http://127.0.0.1:8000/ (mounted last so /graphql wins)
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="frontend")
