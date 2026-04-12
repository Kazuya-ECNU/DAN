"""
DAN Web API — FastAPI + SSE streaming
POST /api/run   → returns immediately with task_id
GET  /api/stream/{task_id} → SSE stream of dan output (supports reconnect)
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path

import fastapi
import fastapi.responses as responses
import uvicorn
from fastapi import FastAPI, Body
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="DAN Web", version="0.1.0")

BASE_DIR = Path(__file__).resolve().parent.parent  # web/
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# ── Task store: task_id → {queue, producer_started, finished} ────────────────
# Queues allow multiple SSE consumers (reconnects) to share the same stream
task_queues: dict[str, asyncio.Queue] = {}
task_finished: dict[str, asyncio.Event] = {}


# ── SSE mock data generator ──────────────────────────────────────────────────
async def mock_stream(task_id: str, meta: str, heuristic: str, param: str, loss: str):
    """Simulate dan --json streaming output with realistic delays."""
    await asyncio.sleep(0.05)

    # Echo the four components
    yield {"type": "echo_banner", "text": "META ─────────────────────────────────────"}
    for line in (meta or "(空)").splitlines()[:20]:
        if line.strip():
            yield {"type": "echo", "label": "META", "text": line}
        await asyncio.sleep(0.005)

    yield {"type": "echo_banner", "text": "HEURISTIC ─────────────────────────────────"}
    for line in (heuristic or "(空)").splitlines()[:20]:
        if line.strip():
            yield {"type": "echo", "label": "HEURISTIC", "text": line}
        await asyncio.sleep(0.005)

    yield {"type": "echo_banner", "text": "PARAM ──────────────────────────────────────"}
    for line in (param or "(空)").splitlines()[:30]:
        if line.strip():
            yield {"type": "echo", "label": "PARAM", "text": line}
        await asyncio.sleep(0.003)

    yield {"type": "echo_banner", "text": "LOSS ────────────────────────────────────────"}
    for line in (loss or "(空)").splitlines()[:30]:
        if line.strip():
            yield {"type": "echo", "label": "LOSS", "text": line}
        await asyncio.sleep(0.003)

    yield {"type": "section", "text": "🚀 开始执行 DAN 优化循环"}

    # Iteration 1
    await asyncio.sleep(0.2)
    yield {"type": "section", "text": "▓▓ Iteration 1 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"}
    await asyncio.sleep(0.1)
    yield {"type": "section", "text": "📋 META — 代码质量优化"}
    yield {"type": "section", "text": "🧠 HEURISTIC — 手动调参，不超过5轮"}
    yield {"type": "loss", "metrics": {
        "loc": 290, "avg_cc": 5.77, "avg_func_loc": 21.2,
        "dup_rate": 20.7, "halstead_diff": 5.2, "mi": 32.7
    }}
    yield {"type": "log", "text": "  ⚙️  Compute LOSS → avg_cc: 5.77, mi: 32.70"}
    await asyncio.sleep(0.15)
    yield {"type": "log", "text": "  ⚙️  Apply HEURISTIC → strategy: MarkdownHeuristicStrategy"}
    yield {"type": "log", "text": "  ⚙️  PARAM: 无更新 (人机协同模式)"}
    yield {"type": "section", "text": "⏸  请参考上方 HEURISTIC 规则，手动调整 PARAM 后继续"}

    # Iteration 2
    await asyncio.sleep(0.3)
    yield {"type": "section", "text": "▓▓ Iteration 2 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"}
    await asyncio.sleep(0.1)
    yield {"type": "loss", "metrics": {
        "loc": 285, "avg_cc": 5.20, "avg_func_loc": 19.0,
        "dup_rate": 18.5, "halstead_diff": 4.9, "mi": 34.1
    }}
    yield {"type": "log", "text": "  ⚙️  Compute LOSS → avg_cc: 5.20, mi: 34.10 (↑改善)"}
    yield {"type": "log", "text": "  ⚙️  Apply HEURISTIC → 消除重复代码块 (重构中...)"}
    await asyncio.sleep(0.2)
    yield {"type": "param_update", "files": ["demo.py"]}
    yield {"type": "log", "text": "  ✅ PARAM 已更新: demo.py (减少重复逻辑)"}

    # Iteration 3
    await asyncio.sleep(0.3)
    yield {"type": "section", "text": "▓▓ Iteration 3 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"}
    await asyncio.sleep(0.1)
    yield {"type": "loss", "metrics": {
        "loc": 259, "avg_cc": 2.90, "avg_func_loc": 8.5,
        "dup_rate": 8.10, "halstead_diff": 5.00, "mi": 35.50
    }}
    yield {"type": "log", "text": "  ⚙️  Compute LOSS → avg_cc: 2.90, mi: 35.50 (显著改善)"}
    yield {"type": "log", "text": "  ⚙️  Apply HEURISTIC → 提取公共函数，进一步简化"}
    await asyncio.sleep(0.2)
    yield {"type": "param_update", "files": ["demo.py"]}
    yield {"type": "log", "text": "  ✅ PARAM 已更新: demo.py"}

    await asyncio.sleep(0.2)
    yield {"type": "done", "reason": "达到最大迭代次数 (max_iterations=3)", "iterations": 3}
    yield {"type": "section", "text": "✅ 优化完成 — 共 3 次迭代"}


async def start_task_producer(task_id: str, meta: str, heuristic: str, param: str, loss: str):
    """Run mock_stream and put all events into the task's queue. Signal finished when done."""
    q = task_queues[task_id]
    try:
        async for event in mock_stream(task_id, meta, heuristic, param, loss):
            await q.put(event)
        # Sentinel: None means producer is done
        await q.put(None)
    except asyncio.CancelledError:
        pass
    finally:
        task_finished[task_id].set()


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root(request: fastapi.Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/run")
async def run_task(body: dict = Body(default={})):
    """Register a task and return its ID."""
    meta = body.get("meta", "")
    heuristic = body.get("heuristic", "")
    param = body.get("param", "")
    loss = body.get("loss", "")
    task_id = str(uuid.uuid4())[:8]
    # Create shared queue for this task
    task_queues[task_id] = asyncio.Queue()
    task_finished[task_id] = asyncio.Event()
    # Start producer in background (detached — does not block)
    asyncio.create_task(start_task_producer(task_id, meta, heuristic, param, loss))
    return {"task_id": task_id}


@app.get("/api/stream/{task_id}")
async def stream_task(task_id: str):
    """SSE stream for a task. Supports reconnect — shares the same queue."""
    if task_id not in task_queues:
        return responses.JSONResponse({"error": "Task not found"}, status_code=404)

    q = task_queues[task_id]

    async def event_generator():
        # Serve events from the shared queue.
        # If the stream already finished and queue is drained (reconnect after done),
        # yield a 'close' event immediately so the browser doesn't hang.
        while True:
            if q.empty() and task_finished[task_id].is_set():
                yield f"data: {json.dumps({'type': 'close'}, ensure_ascii=False)}\n\n"
                break
            try:
                event = await asyncio.wait_for(q.get(), timeout=3.0)
            except asyncio.TimeoutError:
                # Timeout means no new event after 3s — stream is still live but quiet
                continue
            if event is None:
                # Sentinel: producer is done
                yield f"data: {json.dumps({'type': 'close'}, ensure_ascii=False)}\n\n"
                break
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return responses.StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3847)
