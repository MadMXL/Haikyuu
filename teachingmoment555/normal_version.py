# STEP 2 — the normal way (see README.md)
#
# Run:   uvicorn normal_version:app --reload
# Test:  curl.exe http://127.0.0.1:8000/normal

import asyncio  # lets us pause with await asyncio.sleep() without freezing the server
from fastapi import FastAPI  # the framework itself, gives us @app.get() etc.

app = FastAPI()  # create the actual app instance uvicorn will run

@app.get("/")  # register this function to handle GET requests to "/"
def hello():
    return {"message": "Hello, World!"}  # sent back immediately, no delay here

@app.get("/normal")  # register this function to handle GET requests to "/normal"
async def slow_normal():
    lines = []  # empty list that will collect every chunk before anything is sent
    for i in range(1, 6):  # loop 5 times, i = 1, 2, 3, 4, 5
        await asyncio.sleep(1)  # pretend this row took 1 second to prepare (e.g. a slow DB call)
        lines.append(f"chunk {i}")  # add the finished row to the list, nothing sent yet
    return {"data": lines}  # only NOW, after all 5 rows exist, does anything go to the client
