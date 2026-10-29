# STEP 7 — big data, and why you should batch (see README.md)
#
# Run:   uvicorn big_data_version:app --reload
# Test:  curl.exe -s -N -o NUL -w "first byte %{time_starttransfer}s, total %{time_total}s\n" http://127.0.0.1:8000/export-normal
#        (repeat with /export-stream and /export-stream-per-row)

import asyncio
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, StreamingResponse

app = FastAPI()

ROWS = 200_000  # total rows
BATCH = 20_000  # rows per "database fetch" -> 10 fetches


async def fetch_batch(start):
    await asyncio.sleep(0.5)  # pretend the database takes 0.5s per batch
    return [f"row {i}\n" for i in range(start, start + BATCH)]


@app.get("/export-normal")  # wait for everything, then send
async def export_normal():
    rows = []
    for start in range(0, ROWS, BATCH):
        rows += await fetch_batch(start)
    return PlainTextResponse("".join(rows))


@app.get("/export-stream")  # send each batch as soon as it's ready (10 sends)
async def export_stream():
    async def generate():
        for start in range(0, ROWS, BATCH):
            batch = await fetch_batch(start)
            yield "".join(batch)

    return StreamingResponse(generate(), media_type="text/plain")


@app.get("/export-stream-per-row")  # same, but send every row on its own (200,000 sends)
async def export_stream_per_row():
    async def generate():
        for start in range(0, ROWS, BATCH):
            for row in await fetch_batch(start):
                yield row

    return StreamingResponse(generate(), media_type="text/plain")
