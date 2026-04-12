"""
DAN Web API — FastAPI + SSE streaming
POST /api/run   → returns immediately with task_id
GET  /api/stream/{task_id} → SSE stream of dan output (supports reconnect)
"""

import asyncio
import json
import uuid
from pathlib import Path

import fastapi.responses as responses
import uvicorn
from fastapi import FastAPI, Body
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="DAN Web", version="0.1.0")

BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

task_queues: dict[str, asyncio.Queue] = {}
task_finished: dict[str, asyncio.Event] = {}

# ── 新增：从 config.json 读取敏感配置 ─────────────────────────────────────
CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

# 提取配置项（可选：方便直接调用）
OPENCLAW_BASE_URL = config["OPENCLAW_BASE_URL"]
GATEWAY_TOKEN = config["GATEWAY_TOKEN"]
X_OPENCLAW_AGENT_ID = config["X_OPENCLAW_AGENT_ID"]
APP_HOST = config["APP_HOST"]
APP_PORT = config["APP_PORT"]


# ── 修复完成：OpenClaw Gateway 对接代码 ─────────────────────────────────
async def mock_stream(task_id: str, meta: str, heuristic: str, param: str, loss: str):
    import httpx

    API_ENDPOINT = f"{OPENCLAW_BASE_URL}/v1/chat/completions"

    prompt_content = f"""
请基于以下参数处理任务：
【META配置】
{meta or "无"}
【启发式规则】
{heuristic or "无"}
【运行参数】
{param or "无"}
【损失函数配置】
{loss or "无"}
请给出完整的处理结果和分析：
"""

    request_body = {
        # ✅ 修复：model 格式改为 openclaw 或 openclaw/<agentId>
        "model": "openclaw",  # 最简单的通用格式，100% 兼容
        # 或者用你的 agent："model": "openclaw/main",
        "messages": [{"role": "user", "content": prompt_content}],
        "stream": True,
        "temperature": 0.7
    }

    headers = {
        "Authorization": f"Bearer {GATEWAY_TOKEN}",
        "Content-Type": "application/json",
        "x-openclaw-agent-id": "main"
    }

    try:
        async with httpx.AsyncClient(timeout=1200) as client:
            async with client.stream("POST", API_ENDPOINT, json=request_body, headers=headers) as response:
                if response.status_code != 200:
                    err = await response.aread()
                    yield {"type": "echo", "label": "ERROR", "text": f"API错误 {response.status_code}: {err.decode('utf-8', errors='replace')}"}
                    return

                buffer = ""
                async for chunk in response.aiter_bytes():
                    buffer += chunk.decode("utf-8", errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            content = data["choices"][0]["delta"].get("content", "")
                            if content:
                                yield {"type": "echo", "label": "OPENCLAW", "text": content}
                        except json.JSONDecodeError:
                            continue

        yield {"type": "echo", "label": "SYSTEM", "text": "✅ 任务完成"}

    except httpx.ConnectError:
        yield {"type": "echo", "label": "ERROR", "text": "无法连接 OpenClaw Gateway (127.0.0.1:18789)"}
    except Exception as e:
        yield {"type": "echo", "label": "ERROR", "text": f"异常：{str(e)}"}


async def start_task_producer(task_id: str, meta: str, heuristic: str, param: str, loss: str):
    q = task_queues[task_id]
    try:
        async for event in mock_stream(task_id, meta, heuristic, param, loss):
            await q.put(event)
        await q.put(None)
    except asyncio.CancelledError:
        pass
    finally:
        task_finished[task_id].set()


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return responses.FileResponse(str(BASE_DIR / "templates" / "index.html"))


@app.post("/api/run")
async def run_task(body: dict = Body(default={})):
    meta = body.get("meta", "")
    heuristic = body.get("heuristic", "")
    param = body.get("param", "")
    loss = body.get("loss", "")
    task_id = str(uuid.uuid4())[:8]
    task_queues[task_id] = asyncio.Queue()
    task_finished[task_id] = asyncio.Event()
    asyncio.create_task(start_task_producer(task_id, meta, heuristic, param, loss))
    return {"task_id": task_id}


@app.get("/api/stream/{task_id}")
async def stream_task(task_id: str):
    if task_id not in task_queues:
        return responses.JSONResponse({"error": "Task not found"}, status_code=404)

    q = task_queues[task_id]

    async def event_generator():
        while True:
            if q.empty() and task_finished[task_id].is_set():
                yield f"data: {json.dumps({'type': 'close'}, ensure_ascii=False)}\n\n"
                break

            try:
                # ✅ 修复：把 3秒 改成 180秒 超时，防止SSE断开
                event = await asyncio.wait_for(q.get(), timeout=180.0)
            except asyncio.TimeoutError:
                continue

            if event is None:
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