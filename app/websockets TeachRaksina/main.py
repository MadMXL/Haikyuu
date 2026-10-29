# -*- coding: utf-8 -*-
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


app = FastAPI()


# --- Database (SQLite file next to this main.py, so data survives restarts) ---
sqlite_file_name = Path(__file__).parent / "products.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ProductDB(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    stock = Column(Integer, nullable=False, default=0)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Seed a couple of rows the first time the database is created
with SessionLocal() as db:
    if db.query(ProductDB).count() == 0:
        db.add_all([
            ProductDB(id=1, name="Laptop", stock=10),
            ProductDB(id=2, name="Mouse", stock=50),
        ])
        db.commit()


# --- Schema ---
class Product(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    stock: int


# --- Connection Manager ---
class ConnectionManager:

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # Iterate over a copy: a dead client must not stop the others from getting the message
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


# --- WebSocket Endpoint ---
@app.websocket("/ws/products")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await manager.broadcast({"event": "ONLINE_COUNT", "count": len(manager.active_connections)})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast({"event": "ONLINE_COUNT", "count": len(manager.active_connections)})


# --- READ ---
@app.get("/products", response_model=list[Product])
async def get_all_products(db: Session = Depends(get_db)):
    return db.query(ProductDB).order_by(ProductDB.id).all()


# --- CREATE ---
@app.post("/products", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(product: Product, db: Session = Depends(get_db)):
    if db.get(ProductDB, product.id):
        raise HTTPException(status_code=400, detail=f"Product with ID {product.id} already exists")

    db_product = ProductDB(**product.model_dump())
    db.add(db_product)
    db.commit()

    await manager.broadcast({"event": "PRODUCT_CREATED", "product": product.model_dump()})
    return product


# --- UPDATE ---
@app.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: int, updated_product: Product, db: Session = Depends(get_db)):
    if updated_product.id != product_id:
        raise HTTPException(status_code=400, detail="Path id and body id must match")

    db_product = db.get(ProductDB, product_id)
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    db_product.name = updated_product.name
    db_product.stock = updated_product.stock
    db.commit()

    await manager.broadcast({"event": "STOCK_UPDATED", "product": updated_product.model_dump()})
    return updated_product


# --- DELETE ---
@app.delete("/products/{product_id}")
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_product = db.get(ProductDB, product_id)
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    deleted = Product.model_validate(db_product)
    db.delete(db_product)
    db.commit()

    await manager.broadcast({"event": "PRODUCT_DELETED", "product": deleted.model_dump()})
    return {"message": "Delete product successfully", "data": deleted}


# --- FAQ Chatbot (rule-based: matches keywords, answers from the live database) ---
LOW_STOCK_LIMIT = 10

HELP_TEXT = (
    "You can ask me things like:\n"
    "- list all products\n"
    "- how many laptop? / stock of mouse / product id 2\n"
    "- which products are low stock? / out of stock?\n"
    "- which product has the most stock?\n"
    "- total stock\n"
    "- how do I add / update / delete a product?\n"
    "- how does the realtime update work?"
)


def has_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def format_product(p: ProductDB) -> str:
    return f"#{p.id} {p.name}: {p.stock} in stock"


def chatbot_answer(question: str, db: Session) -> str:
    text = question.lower().strip()
    products = db.query(ProductDB).order_by(ProductDB.id).all()

    if has_any(text, ["hello", "hi", "hey", "สวัสดี"]) and len(text) < 20:
        return "Hello! I'm the product FAQ bot.\n" + HELP_TEXT
    if has_any(text, ["help", "what can you", "ช่วย"]):
        return HELP_TEXT

    # How-to questions come first, so "how do I update laptop" is not read as a stock question
    if has_any(text, ["how", "วิธี"]):
        if has_any(text, ["add", "create", "new", "เพิ่ม"]):
            return ("Use the 'Add product' form on this page, or in Postman:\n"
                    'POST /products with JSON body {"id": 3, "name": "Keyboard", "stock": 7}')
        if has_any(text, ["update", "edit", "change", "แก้"]):
            return ("Change the name or stock in the table and press Enter, or in Postman:\n"
                    'PUT /products/{id} with JSON body {"id": 1, "name": "Laptop", "stock": 3}\n'
                    "The id in the URL and the body must match.")
        if has_any(text, ["delete", "remove", "ลบ"]):
            return "Click Delete on the row, or in Postman: DELETE /products/{id}"
    if has_any(text, ["websocket", "realtime", "real-time", "real time", "refresh", "live"]):
        return ("Every page keeps a WebSocket open to /ws/products. When a product is created, "
                "updated or deleted, the server broadcasts an event (PRODUCT_CREATED, STOCK_UPDATED, "
                "PRODUCT_DELETED) to all pages, and each page updates its table without refreshing.")

    if not products:
        return "There are no products in the database right now."

    # A question about one specific product (by name or by id)
    for p in products:
        if p.name.lower() in text:
            return format_product(p)
    for word in text.replace("#", " ").split():
        if word.isdigit() and has_any(text, ["id", "#", "product"]):
            p = db.get(ProductDB, int(word))
            return format_product(p) if p else f"There is no product with id {word}."

    # Not a bare "หมด": it is also inside "ทั้งหมด" (all)
    if has_any(text, ["out of stock", "หมดสต็อก", "สินค้าหมด", "ของหมด"]):
        empty = [p for p in products if p.stock == 0]
        return "\n".join(map(format_product, empty)) if empty else "Nothing is out of stock."
    if has_any(text, ["low", "running out", "ใกล้หมด", "น้อย"]):
        low = [p for p in products if p.stock < LOW_STOCK_LIMIT]
        if not low:
            return f"No product has less than {LOW_STOCK_LIMIT} in stock."
        return f"Products with less than {LOW_STOCK_LIMIT} in stock:\n" + "\n".join(map(format_product, low))
    if has_any(text, ["most", "highest", "max", "มากที่สุด"]):
        return "Most stock: " + format_product(max(products, key=lambda p: p.stock))
    if has_any(text, ["least", "lowest", "min", "น้อยที่สุด"]):
        return "Least stock: " + format_product(min(products, key=lambda p: p.stock))
    if has_any(text, ["total", "sum", "count", "how many", "รวม", "กี่"]):
        return f"There are {len(products)} products with {sum(p.stock for p in products)} items in stock in total."
    if has_any(text, ["list", "all", "products", "show", "ทั้งหมด", "สินค้า"]):
        return "\n".join(map(format_product, products))

    return "Sorry, I don't understand that yet.\n" + HELP_TEXT


# Each visitor talks to the bot privately, so replies are sent back only to the asker (no broadcast)
@app.websocket("/ws/chatbot")
async def chatbot_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"from": "bot", "text": "Hi! Ask me about the products. Type 'help' to see examples."})
    try:
        while True:
            question = await websocket.receive_text()
            if not question.strip():
                continue
            with SessionLocal() as db:
                answer = chatbot_answer(question, db)
            await websocket.send_json({"from": "bot", "text": answer})
    except WebSocketDisconnect:
        pass


# --- HTML UI: live table + forms, updated by WebSocket messages ---
html_code = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Live Products</title>
<style>
  body { font-family: sans-serif; max-width: 720px; margin: 24px auto; padding: 0 16px; }
  table { width: 100%; border-collapse: collapse; margin: 12px 0; }
  th, td { border-bottom: 1px solid #ddd; padding: 6px; text-align: left; }
  input { width: 90px; }
  .status { font-size: 14px; }
  .on { color: green; } .off { color: red; }
  .flash { animation: flash 1s; }
  @keyframes flash { from { background: #fff3a0; } to { background: transparent; } }
  #log { font-size: 13px; color: #555; max-height: 160px; overflow-y: auto; }
  #bot { position: fixed; right: 16px; bottom: 16px; width: 320px; max-width: calc(100vw - 32px);
         background: white; border: 1px solid #ccc; border-radius: 10px; box-shadow: 0 4px 16px rgba(0,0,0,.15); }
  #botHeader { background: #0b84ff; color: white; padding: 8px 12px; border-radius: 10px 10px 0 0; cursor: pointer; }
  #botMessages { height: 260px; overflow-y: auto; padding: 8px; font-size: 14px; }
  .bm { margin: 6px 0; white-space: pre-line; }
  .bm span { display: inline-block; padding: 6px 10px; border-radius: 10px; background: #eee; max-width: 85%; }
  .bm.user { text-align: right; }
  .bm.user span { background: #0b84ff; color: white; }
  #botForm { display: flex; gap: 6px; padding: 8px; border-top: 1px solid #eee; }
  #botInput { flex: 1; width: auto; }
</style>
</head>
<body>
<h2>Products (live)</h2>
<div class="status">Connection: <b id="conn" class="off">connecting...</b> | Online: <b id="online">-</b></div>

<table>
  <thead><tr><th>ID</th><th>Name</th><th>Stock</th><th></th></tr></thead>
  <tbody id="rows"></tbody>
</table>

<h3>Add product</h3>
<form id="addForm">
  <input name="id" type="number" placeholder="id" required>
  <input name="name" placeholder="name" required>
  <input name="stock" type="number" placeholder="stock" required>
  <button>Add</button>
</form>

<h3>Activity</h3>
<div id="log"></div>

<div id="bot">
  <div id="botHeader" onclick="toggleBot()">FAQ Chatbot</div>
  <div id="botBody">
    <div id="botMessages"></div>
    <form id="botForm">
      <input id="botInput" placeholder="Ask about products..." autocomplete="off">
      <button>Send</button>
    </form>
  </div>
</div>

<script>
const products = new Map();

function render(flashId) {
  const rows = [...products.values()].sort((a, b) => a.id - b.id).map(p => `
    <tr id="row-${p.id}" class="${p.id === flashId ? "flash" : ""}">
      <td>${p.id}</td>
      <td><input value="${p.name}" onchange="save(${p.id}, this)" data-field="name"></td>
      <td><input type="number" value="${p.stock}" onchange="save(${p.id}, this)" data-field="stock"></td>
      <td><button onclick="removeProduct(${p.id})">Delete</button></td>
    </tr>`);
  document.getElementById("rows").innerHTML = rows.join("");
}

function log(text) {
  const line = document.createElement("div");
  line.textContent = new Date().toLocaleTimeString() + "  " + text;
  document.getElementById("log").prepend(line);
}

async function loadAll() {
  const res = await fetch("/products");
  products.clear();
  for (const p of await res.json()) products.set(p.id, p);
  render();
}

async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) alert((await res.json()).detail);
}

function save(id, input) {
  const p = { ...products.get(id) };
  p[input.dataset.field] = input.type === "number" ? Number(input.value) : input.value;
  api("PUT", "/products/" + id, p);
}

function removeProduct(id) {
  api("DELETE", "/products/" + id);
}

document.getElementById("addForm").onsubmit = (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  api("POST", "/products", { id: Number(f.get("id")), name: f.get("name"), stock: Number(f.get("stock")) });
  e.target.reset();
};

// --- WebSocket: apply each event directly to the table, reconnect if dropped ---
function connect() {
  const protocol = location.protocol === "https:" ? "wss://" : "ws://";
  const ws = new WebSocket(protocol + location.host + "/ws/products");
  const conn = document.getElementById("conn");

  ws.onopen = () => {
    conn.textContent = "connected"; conn.className = "on";
    loadAll();  // catch up on anything missed while disconnected
  };

  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    const p = msg.product;
    if (msg.event === "ONLINE_COUNT") {
      document.getElementById("online").textContent = msg.count;
    } else if (msg.event === "PRODUCT_CREATED") {
      products.set(p.id, p); render(p.id); log(`Created ${p.name} (stock ${p.stock})`);
    } else if (msg.event === "STOCK_UPDATED") {
      products.set(p.id, p); render(p.id); log(`Updated ${p.name} -> stock ${p.stock}`);
    } else if (msg.event === "PRODUCT_DELETED") {
      products.delete(p.id); render(); log(`Deleted ${p.name}`);
    }
  };

  ws.onclose = () => {
    conn.textContent = "disconnected, retrying..."; conn.className = "off";
    setTimeout(connect, 2000);
  };
}

connect();

// --- FAQ Chatbot: its own WebSocket, replies only come back to this page ---
let botWs;

function botSay(text, who) {
  const box = document.getElementById("botMessages");
  const div = document.createElement("div");
  div.className = "bm " + who;
  const span = document.createElement("span");
  span.textContent = text;  // textContent, so replies are never run as HTML
  div.appendChild(span);
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function connectBot() {
  const protocol = location.protocol === "https:" ? "wss://" : "ws://";
  botWs = new WebSocket(protocol + location.host + "/ws/chatbot");
  botWs.onmessage = (e) => botSay(JSON.parse(e.data).text, "bot");
  botWs.onclose = () => setTimeout(connectBot, 2000);
}

function toggleBot() {
  const body = document.getElementById("botBody");
  body.style.display = body.style.display === "none" ? "block" : "none";
}

document.getElementById("botForm").onsubmit = (e) => {
  e.preventDefault();
  const input = document.getElementById("botInput");
  if (input.value.trim() && botWs.readyState === WebSocket.OPEN) {
    botSay(input.value, "user");
    botWs.send(input.value);
    input.value = "";
  }
};

connectBot();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def get_ui():
    return html_code
