import time
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI

app = FastAPI()

LOG_FILE = Path(__file__).with_name("notifications.txt")


@app.get("/")
def home():
    return {"message": "Background Tasks Demo"}


def write_notification(message: str):
    print(f"START: {message}", flush=True)

    time.sleep(5)

    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(message + "\n")

    print(f"DONE: {message}", flush=True)


@app.post("/normal")
def normal_notification(message: str):
    write_notification(message)

    return {"message": "Notification saved"}

@app.post("/background", status_code=202)
def background_notification(
    message: str,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(write_notification, message)

    return {"message": "Request accepted; notification will be saved"}