# STEP 11 — your turn (see README.md)
#
# Run:   uvicorn exercise_version:app --reload --port 8003
# Test:  curl.exe -N http://127.0.0.1:8003/report-stream
#
# TASK: /report-stream works like /report right now (6 seconds of nothing).
#       Change it so each line is sent as soon as it's ready.
#       The answer is at the bottom. Try first!

import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

SECTIONS = ["sales", "refunds", "inventory", "shipping", "reviews", "summary"]


async def build_section(name):
    await asyncio.sleep(1)  # pretend each section is a slow query
    return f"{name}: ok"


@app.get("/report")  # the normal way, leave this one alone
async def report():
    lines = []
    for name in SECTIONS:
        lines.append(await build_section(name))
    return {"data": lines}


@app.get("/report-stream")  # TODO: make this one stream
async def report_stream():
    lines = []
    for name in SECTIONS:
        lines.append(await build_section(name))
    return {"data": lines}


# ANSWER:
#
# @app.get("/report-stream")
# async def report_stream():
#     async def generate():
#         for name in SECTIONS:
#             yield await build_section(name) + "\n"
#
#     return StreamingResponse(generate(), media_type="text/plain")
