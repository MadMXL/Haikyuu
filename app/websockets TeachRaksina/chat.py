# -*- coding: utf-8 -*-
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse


app = FastAPI()


# --- Connection Manager: remembers who is in the room ---
class ConnectionManager:

    def __init__(self):
        self.active_connections: dict[WebSocket, str] = {}  # websocket -> username

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[websocket] = username

    def disconnect(self, websocket: WebSocket):
        self.active_connections.pop(websocket, None)

    def online_users(self) -> list[str]:
        return list(self.active_connections.values())

    async def broadcast(self, message: dict):
        # Iterate over a copy: a dead client must not stop the others from getting the message
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


def now() -> str:
    return datetime.now().strftime("%H:%M:%S")


# --- WebSocket Endpoint: ws://localhost:8000/ws/chat?username=Alice ---
@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket, username: str = "Anonymous"):
    await manager.connect(websocket, username)
    await manager.broadcast({"type": "system", "text": f"{username} joined the chat", "time": now(),
                             "users": manager.online_users()})
    try:
        while True:
            text = (await websocket.receive_text()).strip()
            if text:
                await manager.broadcast({"type": "chat", "username": username, "text": text, "time": now()})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast({"type": "system", "text": f"{username} left the chat", "time": now(),
                                 "users": manager.online_users()})


# --- HTML UI ---
html_code = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Chat Room</title>
<style>
  body { font-family: sans-serif; max-width: 640px; margin: 24px auto; padding: 0 16px; }
  #messages { height: 380px; overflow-y: auto; border: 1px solid #ccc; border-radius: 8px; padding: 10px; }
  .msg { margin: 6px 0; }
  .msg .time { color: #999; font-size: 12px; }
  .msg.me { text-align: right; }
  .msg.me .bubble { background: #0b84ff; color: white; }
  .bubble { display: inline-block; background: #eee; padding: 6px 10px; border-radius: 12px; }
  .system { text-align: center; color: #888; font-size: 13px; font-style: italic; }
  form { display: flex; gap: 8px; margin-top: 10px; }
  #text { flex: 1; padding: 8px; }
  .status { font-size: 14px; margin-bottom: 8px; }
</style>
</head>
<body>
<h2>Chat Room</h2>

<div id="login">
  <input id="username" placeholder="Your name" maxlength="20">
  <button onclick="join()">Join</button>
</div>

<div id="room" style="display:none">
  <div class="status">You are <b id="me"></b> | Online (<span id="count">0</span>): <span id="users"></span></div>
  <div id="messages"></div>
  <form id="sendForm">
    <input id="text" placeholder="Type a message..." autocomplete="off">
    <button>Send</button>
  </form>
</div>

<script>
let ws;
let myName;

function join() {
  myName = document.getElementById("username").value.trim() || "Anonymous";
  document.getElementById("login").style.display = "none";
  document.getElementById("room").style.display = "block";
  document.getElementById("me").textContent = myName;
  connect();
}

function connect() {
  const protocol = location.protocol === "https:" ? "wss://" : "ws://";
  ws = new WebSocket(protocol + location.host + "/ws/chat?username=" + encodeURIComponent(myName));

  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    const box = document.getElementById("messages");
    const div = document.createElement("div");

    if (msg.type === "system") {
      div.className = "system";
      div.textContent = msg.time + "  " + msg.text;
      document.getElementById("users").textContent = msg.users.join(", ");
      document.getElementById("count").textContent = msg.users.length;
    } else {
      div.className = "msg" + (msg.username === myName ? " me" : "");
      const who = msg.username === myName ? "" : msg.username + ": ";
      // textContent (not innerHTML) so nobody can inject HTML/JS through a message
      const bubble = document.createElement("span");
      bubble.className = "bubble";
      bubble.textContent = who + msg.text;
      const time = document.createElement("div");
      time.className = "time";
      time.textContent = msg.time;
      div.append(bubble, time);
    }

    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  };

  ws.onclose = () => setTimeout(connect, 2000);  // auto-reconnect
}

document.getElementById("sendForm").onsubmit = (e) => {
  e.preventDefault();
  const input = document.getElementById("text");
  if (input.value.trim() && ws.readyState === WebSocket.OPEN) {
    ws.send(input.value);
    input.value = "";
  }
};

document.getElementById("username").addEventListener("keydown", (e) => { if (e.key === "Enter") join(); });
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def get_ui():
    return html_code
