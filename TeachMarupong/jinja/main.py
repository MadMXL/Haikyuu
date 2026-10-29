from fastapi import FastAPI, Form, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse,RedirectResponse

app = FastAPI()
templates = Jinja2Templates(directory="templates")

items_db = [
    {"id": 1, "name": "a", "amount": 5},
    {"id": 2, "name": "b", "amount": 10},
    {"id": 3, "name": "c", "amount": 15},
]

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, template_name="index.html", context={"items": items_db})

@app.post("/items", response_class=RedirectResponse)
async def add_item(name: str = Form(...), amount: int = Form(...)):
  




