from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
import os, uuid

app = FastAPI()

os.makedirs("upload", exist_ok = True)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    name = f"{uuid.uuid4()}.{file.filename.split('.')[-1]}"
    with open(f"upload/{name}","wb") as f:
        f.write(await file.read())
    return {"filename" : name}

@app.get("/files/{filename}")
async def get_file(filename: str):
    if not os.path.exists(f"upload/{filename}"):
        raise HTTPException(404, "not found")
    return FileResponse(f"upload/{filename}")

@app.delete("/files/{filename}")
async def delete_file(filename: str):
    if not os.path.exists(f"upload/{filename}"):
        raise HTTPException(404, "not found")
    os.remove(f"upload/{filename}")
    return{"message": "deleted"}

@app.get("/gallery", response_class=HTMLResponse)
async def gallery():
    files = os.listdir("upload")
    imgs = "".join(f'<img src="/files/{f}">' for f in files)
    return f"""
    <style>
    img {{
        width: 150px;
        height: 150px;
        object-fit: cover;
        margin: 5px;
        border-radius: 8px;
    }}
    </style>
    <h2>Gallery({len(files)})</h2>
    {imgs}
"""