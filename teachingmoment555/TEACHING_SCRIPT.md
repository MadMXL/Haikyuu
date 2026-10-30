# Teaching script — StreamingResponse (40 min)

Keep this open on one screen. Type on the other PC.

- **Grey boxes** = type exactly this.
- **> Quotes** = say this out loud.
- **✅** = what you (and the class) should see.

Only 2 files: `demo.py` (normal + stream) and `client_version.py`.

---

## PART 0 — Brand-new PC (nothing installed, ≈10 min)

You start with: Windows, internet, nothing else.

### 0-1. Check what's already there

Open **PowerShell** (Start → type `powershell` → Enter):
```powershell
python --version
curl.exe --version
```
- `Python 3.10` or newer → skip to 0-3.
- Nothing, or it opens the Microsoft Store → do 0-2.
- `curl.exe` is built into Windows 10/11, so it should always work.

### 0-2. Install Python

```powershell
winget install Python.Python.3.12
```
No `winget`? Download from **python.org/downloads** and, on the first
screen of the installer, **tick "Add python.exe to PATH"**.

**Close PowerShell and open a new one**, then:
```powershell
python --version
```
✅ `Python 3.12.x`

### 0-3. Install VS Code (optional, but easier to type in)

```powershell
winget install Microsoft.VisualStudioCode
```
Or download from **code.visualstudio.com**. Notepad also works — just
save files as `.py`, not `.py.txt`.

---

## PART A — Before class (≈10 min)

### A1. Make the folder

```powershell
mkdir C:\teachingmoment555
cd C:\teachingmoment555
```

### A2. Set up Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn
```
If `Activate.ps1` is blocked:
```powershell
Set-ExecutionPolicy RemoteSigned -Scope Process
.\.venv\Scripts\Activate.ps1
```
✅ The prompt starts with `(.venv)`.

Open a **second PowerShell window** and do the same there:
```powershell
cd C:\teachingmoment555
.\.venv\Scripts\Activate.ps1
```
Window 1 runs the server. Window 2 runs `curl.exe`.

### A3. Type the 2 files — test each one right after

Open the folder in VS Code (`code .`). Comments are optional.

---

#### File 1: `demo.py` (normal + stream in one file)

```python
import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/")
def hello():
    return {"message": "Hello, warodom!"}

@app.get("/normal")
async def normal():
    lines = []
    for i in range(1, 6):
        await asyncio.sleep(1)          # pretend each row takes 1 second
        lines.append(f"chunk {i}")      # nothing sent yet
    return {"data": lines}              # everything sent here, at the end

@app.get("/stream")
async def stream():
    async def generate():
        for i in range(1, 6):
            await asyncio.sleep(1)
            yield f"chunk {i}\n"        # sent right away

    return StreamingResponse(generate(), media_type="text/plain")
```

**Test now** — Window 1:
```powershell
uvicorn demo:app --reload
```
Window 2:
```powershell
curl.exe http://127.0.0.1:8000/normal
curl.exe -N http://127.0.0.1:8000/stream
```
✅ `/normal`: 5 s wait, then `{"data":["chunk 1",...,"chunk 5"]}`.
✅ `/stream`: `chunk 1` … `chunk 5`, one per second.
Ctrl+C in window 1.

---

#### File 2: `client_version.py`

```python
import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

app = FastAPI()

PAGE = """<!doctype html>
<meta charset="utf-8">
<button onclick="streamed()">Stream</button>
<button onclick="allAtOnce()">All at once</button>
<pre id="out"></pre>
<script>
const out = document.getElementById("out");

async function streamed() {
  out.textContent = "";
  const res = await fetch("/live-stream");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    out.textContent += decoder.decode(value);
  }
}

async function allAtOnce() {
  out.textContent = "waiting...";
  const res = await fetch("/live-stream");
  out.textContent = await res.text();
}
</script>
"""


@app.get("/", response_class=HTMLResponse)
def page():
    return PAGE


@app.get("/live-stream")
async def live_stream():
    async def generate():
        try:
            for i in range(1, 11):
                await asyncio.sleep(1)
                print(f"sent row {i}")
                yield f"row {i}\n"
        finally:
            print("cleanup ran")

    return StreamingResponse(generate(), media_type="text/plain")
```

**Test now** — Window 1:
```powershell
uvicorn client_version:app --reload --port 8002
```
Open **http://127.0.0.1:8002/** in the browser and click **Stream**.
✅ `row 1` … `row 10`, one per second; window 1 prints `sent row …` and
`cleanup ran`. Ctrl+C in window 1.

### A4. Before students arrive

Stop every server (Ctrl+C). Both tests passed → you're ready.

---

## PART B — In class

| Time | Step |
|---|---|
| 0:00 | 1. The problem |
| 0:03 | 2. Normal way |
| 0:10 | 3. Streaming way |
| 0:18 | 4. Questions |
| 0:23 | 5. Browser + disconnect |
| 0:35 | 6. Wrap-up |

---

### 1. The problem — 0:00 (talk only)

> "When you ask a server for a lot of data, it usually builds the whole
> answer first. You stare at nothing until it's 100% done. Streaming
> fixes that: it sends you each piece as soon as it's ready."

---

### 2. Normal way — 0:03

Show `demo.py`. Point at the `normal` function: `lines.append` and `return`.

> "We collect every chunk in a list. Each one takes 1 second. Only when
> all 5 are done do we `return`."

**Window 1** (start it once — it serves step 2 and step 3):
```powershell
uvicorn demo:app --reload
```
**Window 2:**
```powershell
curl.exe http://127.0.0.1:8000/normal
```
✅ 5 seconds of nothing, then:
`{"data":["chunk 1","chunk 2","chunk 3","chunk 4","chunk 5"]}`

> "5 seconds of nothing, then everything at once. `return` can't run
> until the whole list is finished."

Leave the server running.

---

### 3. Streaming way — 0:10

Scroll down in `demo.py` to the `stream` function. Point at `yield` and
`StreamingResponse`.

> "Same file, same server. Same loop, same 1-second wait. But instead of
> adding to a list, we `yield` each chunk. `StreamingResponse` sends
> every `yield` to the client right away."

**Window 2** — same server, different URL:
```powershell
curl.exe -N http://127.0.0.1:8000/stream
```
✅ `chunk 1` appears after 1 s, then one more every second.

> "Same 5 seconds, but chunk 1 shows up right away, then one per second.
> The only difference in the code is `yield`."

> "`-N` tells curl: don't wait, print each piece as it comes."

Run both again, one after the other, so they can compare:
```powershell
curl.exe http://127.0.0.1:8000/normal
curl.exe -N http://127.0.0.1:8000/stream
```

Ctrl+C in window 1.

---

### 4. Questions — 0:18 (ask, then wait)

> "Does streaming make the job finish faster?"

Answer: **No.** You just get the first piece sooner, and the server
doesn't hold everything in memory at once.

> "Where would this be useful?"

Let them answer: chat apps / AI answers appearing word by word, big file
downloads, progress updates, live logs.

---

### 5. Browser + disconnect — 0:23

Show `client_version.py`. Point at the two JavaScript functions, then at
`try / finally` in `live_stream`.

**Window 1:**
```powershell
uvicorn client_version:app --reload --port 8002
```
Open **http://127.0.0.1:8002/** in the browser.

- Click **Stream** → ✅ rows appear one by one.
- Click **All at once** → ✅ "waiting..." for 10 s, then everything.

> "Same server. `res.text()` waits for everything; `getReader()` reads
> each piece as it arrives. The browser has to take part too."

Now click **Stream** and **close the tab** after 3 rows.
✅ Window 1 shows `sent row 1…3` then `cleanup ran`.

> "When the user leaves, the server stops. The `finally` block still
> runs, so that's where you close files or database connections."

Ctrl+C in window 1.

---

### 6. Wrap-up — 0:35 (ask the room)

1. Which keyword makes an endpoint stream? → `yield`
2. Is streaming faster overall? → No, it's just faster to *start*.
3. Why `try/finally`? → Cleanup still runs if the user leaves.

**Finished early?** Start `uvicorn demo:app --reload` again and continue
with **TEACHING_SCRIPT_PART2.md**.

---

## If something breaks

| Problem | Fix |
|---|---|
| `Activate.ps1` blocked | `Set-ExecutionPolicy RemoteSigned -Scope Process` |
| `python` not found / opens Store | Python not on PATH → reinstall with "Add to PATH" ticked, open a new PowerShell |
| `No module named fastapi` | venv not active → `.\.venv\Scripts\Activate.ps1` |
| `curl -N` error | Type `curl.exe`, not `curl` |
| Port already in use | Ctrl+C the other server, or use another `--port` |
| `Could not import module` | Wrong folder → `cd C:\teachingmoment555` |
| `{"detail":"Not Found"}` | Wrong port — check which server you're hitting |
| Typo crash on start | Read the last line of the error; it gives the file + line number |

---

## Q & A — questions students might ask

**Basics**

**Q: What is streaming, in one sentence?**
A: The server sends each piece of the answer as soon as it's ready,
instead of waiting until everything is finished.

**Q: Is streaming faster?**
A: Not overall — both `/normal` and `/stream` take 5 seconds. Streaming is
faster to *start*: the user sees the first piece after 1 second instead of 5.

**Q: Then why use it?**
A: The user sees progress right away, so the app feels fast and doesn't
look broken. The server also doesn't have to keep the whole answer in
memory at once.

**Q: What does `yield` do?**
A: It hands back one piece and pauses the function. When the next piece is
needed, the function continues from where it stopped. A function with
`yield` is called a *generator*.

**Q: What's the difference between `return` and `yield`?**
A: `return` sends one answer and the function ends. `yield` can send many
pieces, one at a time, and the function keeps going.

**Q: What does `StreamingResponse` do?**
A: It takes the generator and sends each `yield` to the client as soon as
it comes out.

**Q: Why is `generate()` a function inside another function?**
A: The endpoint has to *return* a response. So we build the generator
inside, and return `StreamingResponse(generate())`, which uses it.

**Q: Why `\n` at the end of each chunk?**
A: So each chunk appears on its own line. Without it, they all print on
one line: `chunk 1chunk 2chunk 3...`

**Q: What is `media_type="text/plain"`?**
A: It tells the client "this is plain text", not JSON or HTML.

**Q: Why do we need `curl.exe -N`?**
A: `-N` turns off curl's buffering. Without it, curl may hold the pieces
and print them all at the end, so streaming looks like it doesn't work.

**Q: What does `await asyncio.sleep(1)` stand for?**
A: Slow work — a slow database query, a big file, an AI model thinking.
We use `sleep` so the delay is easy to see.

**Q: Why `asyncio.sleep` and not `time.sleep`?**
A: `time.sleep` blocks the whole server — nobody else gets served while it
waits. `await asyncio.sleep` lets the server handle other requests in
the meantime.

---

**Browser + disconnect**

**Q: Why did "All at once" wait even though the server streams?**
A: Because `res.text()` waits for the *whole* body. The server streamed,
but the browser didn't read it piece by piece. Both sides must take part.

**Q: What does `getReader()` do?**
A: It reads the response body one piece at a time, as pieces arrive.

**Q: What is `TextDecoder` for?**
A: The pieces arrive as raw bytes. `TextDecoder` turns bytes into text.

**Q: What happens when the user closes the tab?**
A: The connection closes, so the server stops the generator. It doesn't
send the remaining rows.

**Q: Why does `cleanup ran` still print?**
A: Code in `finally` always runs — whether the loop finished normally,
crashed, or the user left halfway.

**Q: What would I put in `finally` in a real app?**
A: Closing a database connection, closing a file, freeing memory, writing
a log line.

---

**Real world**

**Q: Where is streaming used?**
A: ChatGPT / Claude answers appearing word by word, YouTube and Netflix
playing before download finishes, big file downloads and exports, live
logs, progress updates.

**Q: When should I NOT stream?**
A: When the answer is small and fast (a login, one user's profile). Or
when the client needs the whole thing before it can use it, like one JSON
object. Streaming adds complexity for no benefit there.

**Q: Can I send JSON with streaming?**
A: Yes, usually one JSON object per line (called "JSON Lines" or NDJSON).
The client reads and parses each line separately.

**Q: Can I send an error halfway through?**
A: Not as a normal error status — the `200 OK` was already sent with the
first piece. You'd have to send an error message *as a chunk* and let the
client handle it.

**Q: Is this the same as WebSockets?**
A: No. Streaming is one-way: the server sends, the client listens, for one
request. WebSockets are two-way: both sides can send at any time.

**Q: Does this work with `def` instead of `async def`?**
A: Yes. FastAPI also accepts a normal generator (`def` + `yield`). Use
`async def` when you `await` things inside, like `asyncio.sleep`.
