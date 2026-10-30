# Teaching script — Part 2 (extra, ≈10 min)

Use this **only if Part 1 finished early**. It continues straight from
Part 1: same folder, same `demo.py`, same two PowerShell windows.

- **Grey boxes** = type exactly this.
- **> Quotes** = say this out loud.
- **✅** = what you (and the class) should see.

Nothing to install, no new files. You only **add code to the bottom of
`demo.py`**. Because the server runs with `--reload`, it restarts by
itself every time you save — no need to stop it.

| Time | Step | Type? |
|---|---|---|
| +0 | 7. ChatGPT-style typing | `/chat` |
| +5 | 8. Progress bar | `/progress` |
| +8 | 9. Wrap-up 2 | no |

---

## Start (if you stopped the server)

**Window 1:**
```powershell
cd C:\teachingmoment555
.\.venv\Scripts\Activate.ps1
uvicorn demo:app --reload
```
**Window 2:**
```powershell
cd C:\teachingmoment555
.\.venv\Scripts\Activate.ps1
```

---

### 7. ChatGPT-style typing — +0 (≈5 min)

> "Have you noticed ChatGPT or Claude write their answer word by word?
> That's streaming. Let's build a tiny version."

At the **bottom** of `demo.py`, add:
```python


SENTENCE = "Streaming lets the user see the answer while the server is still working on it."

@app.get("/chat")
async def chat():
    async def generate():
        for word in SENTENCE.split():   # split the sentence into words
            await asyncio.sleep(0.3)    # pretend the AI is "thinking"
            yield word + " "            # send one word at a time

    return StreamingResponse(generate(), media_type="text/plain")
```
Save. **Window 2:**
```powershell
curl.exe -N http://127.0.0.1:8000/chat
```
✅ The sentence appears word by word.

> "This is exactly what AI chat apps do. The model makes one word at a
> time, and the server `yield`s each word as soon as it exists. Without
> streaming you'd stare at a blank box until the whole answer was done."

> "Notice there's no `\n` here — we add a space instead, so the words
> stay on one line."

---

### 8. Progress bar — +5 (≈3 min)

> "Another common use: telling the user how far along a long job is."

Add to the **bottom** of `demo.py`:
```python


@app.get("/progress")
async def progress():
    async def generate():
        for percent in range(0, 101, 10):   # 0, 10, 20, ... 100
            await asyncio.sleep(0.5)
            yield f"{percent}% done\n"
        yield "finished!\n"

    return StreamingResponse(generate(), media_type="text/plain")
```
Save. **Window 2:**
```powershell
curl.exe -N http://127.0.0.1:8000/progress
```
✅ `0% done`, `10% done`, … `100% done`, `finished!` — every half second.

> "`range(0, 101, 10)` means: start at 0, stop before 101, step by 10.
> And look — you can `yield` more than once after the loop. `finished!`
> is just one more piece."

---

### 9. Wrap-up 2 — +8 (ask the room)

1. What do `/stream`, `/chat` and `/progress` have in common? → All use
   `async def generate()` + `yield` + `StreamingResponse`.
   **The pattern never changes — only what you `yield`.**
2. Name 3 real apps that stream. → AI chat, video, downloads, progress
   bars, live logs.

> "Every streaming endpoint is the same 3 lines: a generator, `yield`,
> and `StreamingResponse`. If you remember that, you can stream anything."

---

## The pattern (put this on the board)

```python
@app.get("/anything")
async def anything():
    async def generate():
        for ... in ...:
            await ...           # the slow work
            yield ...           # send this piece now

    return StreamingResponse(generate(), media_type="text/plain")
```

---

## Q & A — extra questions for Part 2

**Q: Why didn't I need to restart the server after adding code?**
A: `--reload` watches the files. When you save, uvicorn restarts by itself.

**Q: Why does `/chat` use `" "` instead of `"\n"`?**
A: We want the words on one line, like a sentence. `\n` would put each
word on its own line.

**Q: What does `SENTENCE.split()` do?**
A: Cuts the sentence at every space and gives a list of words:
`["Streaming", "lets", "the", ...]`.

**Q: Do real AI chat apps work exactly like `/chat`?**
A: The idea is the same: the model produces small pieces (tokens), and the
server streams each one. Real apps usually use a format called
Server-Sent Events (`text/event-stream`), but underneath it's still
`yield` + a streaming response.

**Q: What is `range(0, 101, 10)`?**
A: Start at 0, stop *before* 101, step by 10 → 0, 10, 20, … 100.

**Q: Can I `yield` after the loop?**
A: Yes. `yield` can be used anywhere in the generator, any number of times.
`finished!` is an example.

**Q: Where are progress updates used in real life?**
A: File uploads/downloads, installers, video exports, long reports — any
job that takes a while.

---

## If something breaks (Part 2)

| Problem | Fix |
|---|---|
| `IndentationError` | The new code must start at the left edge (no spaces before `@app.get`) |
| `{"detail":"Not Found"}` | You didn't save, or the URL has a typo |
| Server crashed after saving | Read the error in window 1, fix the typo, save again — it restarts by itself |
| Words in `/chat` all appear at once | You forgot `-N` |
