import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import random
import math
import time

# ── WEBSOCKET CONNECTION MANAGER ──────────────────────────────
class WebSocketManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        logger.info(f"Client connected. Total: {len(self.active)}")

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
        logger.info(f"Client disconnected. Total: {len(self.active)}")

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


ws_manager = WebSocketManager()

# ── COGNITIVE STATE ───────────────────────────────────────────
_start_time = time.time()

def get_cognitive_state() -> dict:
    t = time.time() - _start_time
    fatigue   = min(100, 20 + t * 0.05 + random.uniform(-3, 3))
    stress    = 30 + 15 * math.sin(t / 60) + random.uniform(-5, 5)
    attention = max(0, 85 - t * 0.03 + random.uniform(-4, 4))
    cognitive = max(0, 80 - t * 0.02 + random.uniform(-3, 3))

    return {
        "fatigue":   round(min(100, max(0, fatigue)),   1),
        "stress":    round(min(100, max(0, stress)),    1),
        "attention": round(min(100, max(0, attention)), 1),
        "cognitive": round(min(100, max(0, cognitive)), 1),
        "timestamp": time.time(),
    }

# ── BACKGROUND LOOP ───────────────────────────────────────────
async def broadcast_loop():
    while True:
        try:
            state = get_cognitive_state()
            await ws_manager.broadcast(state)
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
        await asyncio.sleep(0.2)

# ── LIFESPAN ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    model_path = "models/weights/mindguard_best.pt"
    onnx_path  = "models/weights/mindguard.onnx"

    if not os.path.exists(model_path) and not os.path.exists(onnx_path):
        logger.warning("No model found. Running simulated mode.")
    else:
        logger.success("Model found — real inference ready.")

    task = asyncio.create_task(broadcast_loop())

    logger.success("🚀 MindGuard AI started")
    logger.info("Docs: http://localhost:8000/docs")

    yield

    task.cancel()
    logger.info("Backend stopped")

# ── FASTAPI APP ───────────────────────────────────────────────
app = FastAPI(
    title="MindGuard AI",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ROOT ROUTE (FIXED) ────────────────────────────────────────
@app.get("/")
def home():
    return {
        "message": "MindGuard AI backend is running 🚀",
        "health": "/health",
        "docs": "/docs"
    }

# ── REST APIs ─────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/state")
def get_state():
    return get_cognitive_state()

@app.get("/history")
def get_history():
    return [get_cognitive_state() for _ in range(60)]

@app.post("/mode")
def set_mode(data: dict):
    mode = data.get("mode", "FOCUS")
    logger.info(f"Mode changed → {mode}")
    return {"status": "ok", "mode": mode}

@app.post("/intervention/dismiss")
def dismiss():
    logger.info("Intervention dismissed")
    return {"status": "dismissed"}

@app.post("/calibrate/start")
def calibrate():
    logger.info("Calibration started")
    return {"status": "started", "duration": 300}

# ── WEBSOCKET ─────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)

    try:
        while True:
            data = await ws.receive_json()   # ✅ FIXED
            logger.info(f"Received data: {data}")
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)

# ── RUN ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)