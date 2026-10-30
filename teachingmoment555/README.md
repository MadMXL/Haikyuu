# StreamingResponse — 40-minute lesson

**The one idea:** normally the server builds the *whole* answer before
sending anything. With `StreamingResponse` + `yield`, it sends each piece
as soon as it's ready.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn
cd teachingmoment555
```
Mac / Linux: `source .venv/bin/activate`, and type `curl` instead of `curl.exe`.

## Plan

| Time | Step | File |
|---|---|---|
| 0:00 | 1. The problem | — |
| 0:03 | 2. Normal way | `demo.py` |
| 0:10 | 3. Streaming way | `demo.py` (same server) |
| 0:18 | 4. Questions | — |
| 0:23 | 5. Browser + disconnect | `client_version.py` |
| 0:35 | 6. Wrap-up | — |

---

### 1. The problem (talk)

> "When you ask a server for a lot of data, it usually builds the whole
> answer first. You stare at nothing until it's 100% done. Streaming
> fixes that: it sends you each piece as soon as it's ready."

### 2. Normal way

Terminal 1 (leave it running for step 3 too):
```powershell
uvicorn demo:app --reload
```
Terminal 2:
```powershell
curl.exe http://127.0.0.1:8000/normal
```
> "5 seconds of nothing, then everything at once. `return` can't run
> until the whole list is finished."

### 3. Streaming way

Same server, just a different URL. Terminal 2:
```powershell
curl.exe -N http://127.0.0.1:8000/stream
```
> "Same 5 seconds, but chunk 1 shows up right away, then one per second.
> The only difference in the code is `yield`."

### 4. Questions (ask, then wait)

- "Does streaming make the job finish faster?"
  → **No.** You just get the first piece sooner, and the server doesn't
  hold everything in memory at once.

### 5. Browser + disconnect

```powershell
uvicorn client_version:app --reload --port 8002
```
Open **http://127.0.0.1:8002/**.

- Click **Stream**. Rows appear one by one.
- Click **All at once**. Nothing for 10 s, then everything.

> "Same server. `res.text()` waits for everything; `getReader()` reads
> each piece as it arrives. The browser has to take part too."

Now click **Stream** and close the tab after 3 rows. The terminal shows
`cleanup ran`.

> "When the user leaves, the server stops. The `finally` block still
> runs, so that's where you close files or database connections."

### 6. Wrap-up (ask the room)

1. Which keyword makes an endpoint stream? → `yield`
2. Is streaming faster overall? → No, it's just faster to *start*.
3. Why `try/finally`? → Cleanup still runs if the user leaves.

---

## If something breaks

- **Activate script blocked (Windows)** → `Set-ExecutionPolicy RemoteSigned -Scope Process`
- **`curl -N` error on Windows** → type `curl.exe`, not `curl`.
- **Port already in use** → stop the other server (Ctrl+C) or use another `--port`.
- **`Could not import module`** → you're in the wrong folder. `cd teachingmoment555`
- **`{"detail":"Not Found"}`** → you're hitting a different server than you think.
  Check the port.
