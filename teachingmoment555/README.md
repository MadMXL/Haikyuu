# StreamingResponse — 40-minute lesson

**The one idea:** normally the server builds the *whole* answer before
sending anything. With `StreamingResponse` + `yield`, it sends each piece
as soon as it's ready.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn sqlalchemy
cd teachingmoment555
```
Mac / Linux: `source .venv/bin/activate`, and type `curl` instead of `curl.exe`.

## Plan

| Time | Step | File |
|---|---|---|
| 0:00 | 1. The problem | — |
| 0:03 | 2. Normal way | `normal_version.py` |
| 0:07 | 3. Streaming way | `stream_version.py` |
| 0:11 | 4. Questions | — |
| 0:15 | 5. Big data + batching | `big_data_version.py` |
| 0:22 | 6. Real database | `db_version.py` |
| 0:26 | 7. Browser + disconnect | `client_version.py` |
| 0:31 | 8. Students try it | `exercise_version.py` |
| 0:38 | 9. Wrap-up | — |

Short on time? Skip step 6.

---

### 1. The problem (talk)

> "When you ask a server for a lot of data, it usually builds the whole
> answer first. You stare at nothing until it's 100% done. Streaming
> fixes that: it sends you each piece as soon as it's ready."

### 2. Normal way

```powershell
uvicorn normal_version:app --reload
curl.exe http://127.0.0.1:8000/normal
```
> "5 seconds of nothing, then everything at once. `return` can't run
> until the whole list is finished."

### 3. Streaming way

In a second terminal:
```powershell
uvicorn stream_version:app --reload --port 8001
curl.exe -N http://127.0.0.1:8001/slow-stream
```
> "Same 5 seconds, but chunk 1 shows up right away, then one per second.
> The only difference in the code is `yield`."

### 4. Questions (ask, then wait)

- "If I replace `yield` with one big `return`, is it normal or streaming?"
  → **Normal.** Everything must be finished before `return`.
- "Does streaming make the job finish faster?"
  → **No.** You just get the first piece sooner, and the server doesn't
  hold everything in memory at once.

### 5. Big data + batching

Stop the step 2 server first (both use port 8000).
```powershell
uvicorn big_data_version:app --reload
curl.exe -s -N -o NUL -w "first byte %{time_starttransfer}s, total %{time_total}s\n" http://127.0.0.1:8000/export-normal
curl.exe -s -N -o NUL -w "first byte %{time_starttransfer}s, total %{time_total}s\n" http://127.0.0.1:8000/export-stream
curl.exe -s -N -o NUL -w "first byte %{time_starttransfer}s, total %{time_total}s\n" http://127.0.0.1:8000/export-stream-per-row
```
(`-o NUL` hides the 200,000 rows and shows only the timings.)

| Endpoint | First byte | Total |
|---|---|---|
| normal | ~5 s | ~5.2 s |
| stream (10 sends) | ~0.01 s | ~5.2 s |
| stream per row (200,000 sends) | ~0.01 s | ~5.4 s, the slowest |

> "Streaming starts right away. But sending every row on its own is
> *slower*, because each send has a small cost. Group rows into batches
> before you `yield`."

### 6. Real database (optional)

Run from the folder **above** `teachingmoment555`:
```powershell
uvicorn teachingmoment555.db_version:app --reload --port 8005
curl.exe http://127.0.0.1:8005/products-normal
curl.exe -N http://127.0.0.1:8005/products-stream
```
> "Same query in both. One collects a list and returns it; the other
> `yield`s each row. Same lesson, real table."

### 7. Browser + disconnect

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

### 8. Students try it

```powershell
uvicorn exercise_version:app --reload --port 8003
curl.exe -N http://127.0.0.1:8003/report-stream
```
Task: make `/report-stream` send one line per second. The answer is at
the bottom of the file. Show it when time is up.

### 9. Wrap-up (ask the room)

1. Which keyword makes an endpoint stream? → `yield`
2. Is streaming faster overall? → No, it's just faster to *start*.
3. Why batch? → Many tiny sends cost more than a few big ones.
4. Why `try/finally`? → Cleanup still runs if the user leaves.

---

## If something breaks

- **Activate script blocked (Windows)** → `Set-ExecutionPolicy RemoteSigned -Scope Process`
- **`curl -N` error on Windows** → type `curl.exe`, not `curl`.
- **Port already in use** → stop the other server (Ctrl+C) or use another `--port`.
- **`Could not import module`** → you're in the wrong folder. `cd teachingmoment555`
  (except step 6, which runs from the folder above it).
- **`{"detail":"Not Found"}`** → you're hitting a different server than you think.
  Check the port.
