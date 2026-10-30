# STEPS 2-3 — normal vs streaming, side by side (see README.md)
#
# Run:   uvicorn demo:app --reload
# Test:  curl.exe http://127.0.0.1:8000/normal
#        curl.exe -N http://127.0.0.1:8000/stream

import asyncio  # lets us pause with await asyncio.sleep() without freezing the server
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/")
def hello():
    return {"message": "Hello, warodom!"}

@app.get("/normal")  # the normal way: build everything, then send it all at once
async def normal():
    lines = []
    for i in range(1, 6):
        await asyncio.sleep(1)  # pretend each row takes 1 second
        lines.append(f"chunk {i}")  # nothing sent yet
    return {"data": lines}  # everything sent here, at the end

@app.get("/stream")  # the streaming way: send each piece as soon as it's ready
async def stream():
    async def generate():
        for i in range(1, 6):
            await asyncio.sleep(1)
            yield f"chunk {i}\n"  # sent right away

    return StreamingResponse(generate(), media_type="text/plain")



SENTENCE = "Streaming lets the user see the answer while the server is still working on it."

@app.get("/chat")
async def chat():
    async def generate():
        for word in SENTENCE.split():   # split the sentence into words
            await asyncio.sleep(0.3)    # pretend the AI is "thinking"
            yield word + " "            # send one word at a time

    return StreamingResponse(generate(), media_type="text/plain")


@app.get("/progress")
async def progress():
    async def generate():
        for percent in range(0, 101, 10):   # 0, 10, 20, ... 100
            await asyncio.sleep(0.5)
            yield f"{percent}% done\n"
        yield "finished!\n"

    return StreamingResponse(generate(), media_type="text/plain")