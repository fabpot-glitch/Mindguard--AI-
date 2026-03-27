import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

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

# ── COGNITIVE STATE (simple simulation until model is trained) ─
import random
import math
import time

_start_time = time.time()

def get_cognitive_state() -> dict:
    """
    Returns simulated cognitive state.
    Replace this with real model inference after training.
    """
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


# ── BACKGROUND BROADCAST TASK ─────────────────────────────────
async def broadcast_loop():
    """Sends cognitive state to all connected WebSocket clients every 200ms"""
    while True:
        try:
            state = get_cognitive_state()
            await ws_manager.broadcast(state)
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
        await asyncio.sleep(0.2)   # 5 times per second


# ── LIFESPAN (startup + shutdown) ─────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Check for model weights
    model_path = "models/weights/mindguard_best.pt"
    onnx_path  = "models/weights/mindguard.onnx"
    if not os.path.exists(model_path) and not os.path.exists(onnx_path):
        logger.warning(
            f"No model found at {model_path} or {onnx_path}\n"
            "Running with simulated data. Train the model first."
        )
    else:
        logger.success("Model weights found — loading real inference.")

    # Start broadcast loop
    task = asyncio.create_task(broadcast_loop())
    logger.success("MindGuard AI backend started on http://0.0.0.0:8000")
    logger.info("API docs available at http://localhost:8000/docs")

    yield   # app runs here

    # Shutdown
    task.cancel()
    logger.info("MindGuard AI backend stopped.")


# ── FASTAPI APP ────────────────────────────────────────────────
app = FastAPI(
    title="MindGuard AI",
    description="Real-time Cognitive Load Prevention System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allows React frontend on port 3000 to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST ENDPOINTS ─────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/state")
def get_state():
    """Returns current cognitive state snapshot"""
    return get_cognitive_state()


@app.get("/history")
def get_history():
    """Returns last 60 state snapshots (placeholder)"""
    history = []
    for i in range(60):
        t = time.time() - (60 - i) * 0.2
        history.append({
            "fatigue":   round(20 + i * 0.05 + random.uniform(-2, 2), 1),
            "stress":    round(30 + 10 * math.sin(i / 10), 1),
            "attention": round(85 - i * 0.03, 1),
            "cognitive": round(80 - i * 0.02, 1),
            "timestamp": t,
        })
    return history


@app.post("/mode")
def set_mode(data: dict):
    """Receives mode change from frontend: FOCUS / MEETING / BREAK"""
    mode = data.get("mode", "FOCUS")
    logger.info(f"Mode changed to: {mode}")
    return {"status": "ok", "mode": mode}


@app.post("/intervention/dismiss")
def dismiss_intervention():
    """Called when user dismisses an intervention"""
    logger.info("Intervention dismissed by user")
    return {"status": "dismissed"}


@app.post("/calibrate/start")
def start_calibration():
    """Starts 5-minute baseline calibration session"""
    logger.info("Calibration started")
    return {"status": "calibration_started", "duration_sec": 300}


# ── WEBSOCKET ENDPOINT ─────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()   # keep connection alive
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


# ── RUN DIRECTLY ───────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )