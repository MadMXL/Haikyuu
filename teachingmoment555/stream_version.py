# STEP 3 — the streaming way (see README.md)
#
# Run:   uvicorn stream_version:app --reload --port 8001
# Test:  curl.exe -N http://127.0.0.1:8001/slow-stream

import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/")
def hello():
    return {"message": "Hello, World!"}

@app.get("/slow-stream")
async def slow_stream():
    async def generate():
        for i in range(1, 6):
            await asyncio.sleep(1)
            yield f"chunk {i}\n"

    return StreamingResponse(generate(), media_type="text/plain")
