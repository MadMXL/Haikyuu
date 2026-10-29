from contextlib import asynccontextmanager
import time
import aiosqlite
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel

@asynccontextmanager
async def lifespan(app: FastAPI):
    #===starup code===
    print("[STARTUP] preparing system...")
    app.state.model = load_model()

    db = await aiosqlite.connect("app.db")
    await db.execute(
        """CREATE TABLE IF NOT EXISTS predictions_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            input_val REAL,
            result_val REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await db.commit()
    app.state.db = db
    print("[STARTUP] connect SQLite(app.db) succeded!")

    try:
        yield
    finally:

        #==shutdown code===
        print("[SHUTDOWN] clear model from memory...")
        app.state.model = None
        await db.close()
        print("[SHUTDOWN] close database and model cleared")

def load_model():
    print("model loading ML... (3 seconds)")
    time.sleep(3)
    print("model loaded!")
    return lambda x: x * 42.0

app = FastAPI(title="Lifespan Demo",lifespan=lifespan)
class PredictIN(BaseModel):
    x: float

@app.get("/")

def read_root():
    return {"status": "online","model_loaded" : app.state.model is not None, "db_connected" : app.state.db is not None}

@app.post("/predict")
async def predict(body: PredictIN):
    model = app.state.model
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not ready")
    result = model(body.x)

    await app.state.db.execute(
        "INSERT INTO predictions_logs (input_val, result_val) VALUES (?, ?)",
        (body.x, result),
    )
    await app.state.db.commit()
    return {"input": body.x, "result": result}

@app.get("/logs")
async def get_logs():
    async with app.state.db.execute("SELECT * FROM predictions_logs ORDER BY id DESC") as cursor:
        rows = await cursor.fetchall()
        logs = [{"id": row[0], "input_val": row[1], "result_val": row[2], "created_at": row[3]} for row in rows]
    return {"total": len(logs), "logs": logs}

@app.get("/predict")
def predict(x: float):
    return {"input": x, "result": app.state.model(x)}