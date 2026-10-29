from fastapi import FastAPI, Request,HTTPException,Depends
from redis.asyncio import Redis

app = FastAPI()

r=Redis(host='localhost', port=6379, decode_responses=True)

@app.get

wsl --install