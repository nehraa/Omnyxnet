#!/usr/bin/env python3
"""
Pangea Net - Industry Demo API Server

This is a lightweight FastAPI wrapper that exposes the core logic via HTTP endpoints.
It serves as the API middleware layer (Tier 2) between the frontend dashboard and
the underlying core logic.

Architecture:
    Browser (UI) ←→ WebSocket/SSE ←→ API Server (This file) ←→ Core Logic

DEMO ONLY: This configuration is for demonstration purposes.
Do not use in production without proper security configuration.
"""
import asyncio
import json
import logging
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Demo configuration
DEMO_DIR = Path(__file__).parent
STATIC_DIR = DEMO_DIR / "static"
SEED_DATA_FILE = DEMO_DIR / "demo_seed.json"

# FastAPI application
app = FastAPI(
    title="Pangea Net Demo API",
    description="Industry demonstration API for Pangea distributed network",
    version="1.0.0-DEMO"
)

# Enable CORS for frontend (demo only - restricted to localhost)
# WARNING: This CORS configuration is for demo purposes only.
# In production, restrict origins and configure proper security.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# State Management
# ============================================================

class DemoState:
    """Manages the demo's runtime state and golden seed data."""
    
    def __init__(self):
        self.data = self.load_seed_data()
        self.start_time = datetime.now()
        self.is_processing = False
        self.processing_lock = asyncio.Lock()  # Protect concurrent access
        self.logs: deque = deque(maxlen=100)  # Thread-safe with auto-limit
        self.execution_count = 0
        
    def load_seed_data(self) -> Dict[str, Any]:
        """Load the golden seed data for consistent demo starts."""
        if SEED_DATA_FILE.exists():
            with open(SEED_DATA_FILE, "r") as f:
                return json.load(f)
        # Default seed data if file doesn't exist
        return {
            "metrics": {
                "files_processed": 150,
                "success_rate": 98.5,
                "nodes_active": 3,
                "compute_tasks": 45,
                "network_latency_ms": 0.33,
                "throughput_mbps": 125.5
            },
            "nodes": [
                {"id": 1, "name": "go-orchestrator", "status": "online", "type": "orchestrator"},
                {"id": 2, "name": "rust-compute", "status": "online", "type": "compute"},
                {"id": 3, "name": "python-ai", "status": "online", "type": "ai-worker"}
            ],
            "recent_tasks": [
                {"id": "task-001", "type": "gradient_sync", "status": "completed", "duration_ms": 45},
                {"id": "task-002", "type": "data_shard", "status": "completed", "duration_ms": 120},
                {"id": "task-003", "type": "ai_inference", "status": "completed", "duration_ms": 89}
            ],
            "system_status": "healthy"
        }
    
    def reset(self) -> None:
        """Reset state to golden seed data."""
        self.data = self.load_seed_data()
        self.logs.clear()
        self.execution_count = 0
        self.add_log("System reset to golden state", "info")
        
    def add_log(self, message: str, level: str = "info") -> None:
        """Add a log entry with timestamp. Thread-safe with deque."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append({
            "timestamp": timestamp,
            "message": message,
            "level": level
        })
        # No manual slicing needed - deque with maxlen handles it
            
    def get_uptime(self) -> str:
        """Get demo uptime as formatted string."""
        delta = datetime.now() - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# Global state instance
state = DemoState()

# ============================================================
# API Endpoints
# ============================================================

@app.get("/")
async def root():
    """Serve the main dashboard."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
async def get_status():
    """
    Returns system health status.
    Used by the frontend to show green/red lights.
    """
    return {
        "status": state.data.get("system_status", "healthy"),
        "version": "1.0.0-DEMO",
        "uptime": state.get_uptime(),
        "is_processing": state.is_processing,
        "nodes": {
            "total": len(state.data.get("nodes", [])),
            "online": sum(1 for n in state.data.get("nodes", []) if n["status"] == "online")
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/data")
async def get_data():
    """
    Fetches the current state/data for tables and graphs.
    Returns metrics, nodes, and recent tasks.
    """
    logs_list = list(state.logs)
    return {
        "metrics": state.data.get("metrics", {}),
        "nodes": state.data.get("nodes", []),
        "recent_tasks": state.data.get("recent_tasks", []),
        "execution_count": state.execution_count,
        "logs": logs_list[-20:]  # Last 20 logs for the terminal view
    }


@app.get("/api/logs")
async def get_logs():
    """Get execution logs for the terminal view."""
    logs_list = list(state.logs)
    return {
        "logs": logs_list[-50:],
        "total_logs": len(logs_list)
    }


async def simulate_processing(complexity: str = "medium"):
    """
    Simulates the distributed processing pipeline.
    This would normally trigger the actual core logic.
    Note: is_processing is set by run_action with lock protection.
    """
    state.add_log("🚀 Initializing distributed pipeline...", "info")
    
    # Complexity affects timing
    delays = {"low": 0.3, "medium": 0.5, "high": 0.8}
    delay = delays.get(complexity, 0.5)
    
    try:
        # Simulate Go orchestrator initialization
        await asyncio.sleep(delay)
        state.add_log("🔗 Go Orchestrator connected (libp2p)", "info")
        
        # Simulate Rust compute core
        await asyncio.sleep(delay)
        state.add_log("⚙️ Rust Compute Core initialized", "info")
        
        # Simulate Python AI worker
        await asyncio.sleep(delay)
        state.add_log("🤖 Python AI Worker ready", "info")
        
        # Simulate data processing
        await asyncio.sleep(delay)
        state.add_log("📊 Processing data shards...", "info")
        
        # Simulate gradient synchronization
        await asyncio.sleep(delay)
        state.add_log("🔄 Gradient synchronization in progress...", "info")
        
        # Update metrics
        metrics = state.data.get("metrics", {})
        metrics["files_processed"] = metrics.get("files_processed", 0) + 10
        metrics["compute_tasks"] = metrics.get("compute_tasks", 0) + 1
        
        # Add completed task
        tasks = state.data.get("recent_tasks", [])
        new_task = {
            "id": f"task-{state.execution_count + 4:03d}",
            "type": ["gradient_sync", "data_shard", "ai_inference"][state.execution_count % 3],
            "status": "completed",
            "duration_ms": int(delay * 5 * 1000)
        }
        tasks.insert(0, new_task)
        state.data["recent_tasks"] = tasks[:10]  # Keep last 10
        
        await asyncio.sleep(delay)
        state.add_log("✅ Task completed successfully!", "success")
        state.execution_count += 1
        
    except Exception as e:
        state.add_log(f"❌ Error: {str(e)}", "error")
        
    finally:
        state.is_processing = False


@app.post("/api/action/run")
async def run_action(
    background_tasks: BackgroundTasks, 
    complexity: str = Query(default="medium", pattern="^(low|medium|high)$")
):
    """
    The Big Button - triggers the main distributed processing logic.
    
    Args:
        complexity: Processing complexity level (low, medium, high)
    """
    # Validate complexity parameter
    valid_complexities = ["low", "medium", "high"]
    if complexity not in valid_complexities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid complexity level. Must be one of: {', '.join(valid_complexities)}"
        )
    
    # Use lock to prevent race conditions
    async with state.processing_lock:
        if state.is_processing:
            raise HTTPException(
                status_code=409,
                detail="Processing already in progress. Please wait."
            )
        state.is_processing = True
    
    # Start processing in background
    background_tasks.add_task(simulate_processing, complexity)
    
    state.add_log(f"📦 Starting execution (complexity: {complexity})...", "info")
    
    return {
        "status": "started",
        "message": f"Execution started with {complexity} complexity",
        "execution_id": state.execution_count + 1
    }


@app.post("/api/reset")
async def reset_demo():
    """
    Wipes the demo state back to the golden seed data.
    Useful for resetting between demo sessions.
    """
    state.reset()
    return {
        "status": "success",
        "message": "Demo state reset to golden data"
    }


@app.get("/api/nodes")
async def get_nodes():
    """Get detailed node information."""
    return {
        "nodes": state.data.get("nodes", []),
        "total": len(state.data.get("nodes", []))
    }


# ============================================================
# Server-Sent Events for Real-Time Updates
# ============================================================

@app.get("/api/events")
async def stream_events(request: Request):
    """
    Server-Sent Events endpoint for real-time dashboard updates.
    More efficient than polling - pushes updates to the client.
    """
    async def event_generator():
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break
            
            # Build combined data
            logs_list = list(state.logs)
            data = {
                "status": {
                    "status": state.data.get("system_status", "healthy"),
                    "version": "1.0.0-DEMO",
                    "uptime": state.get_uptime(),
                    "is_processing": state.is_processing,
                    "nodes": {
                        "total": len(state.data.get("nodes", [])),
                        "online": sum(1 for n in state.data.get("nodes", []) if n["status"] == "online")
                    },
                    "timestamp": datetime.now().isoformat()
                },
                "data": {
                    "metrics": state.data.get("metrics", {}),
                    "nodes": state.data.get("nodes", []),
                    "recent_tasks": state.data.get("recent_tasks", []),
                    "execution_count": state.execution_count,
                    "logs": logs_list[-20:]
                }
            }
            
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(1)  # Push updates every second
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================
# Static File Serving
# ============================================================

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ============================================================
# Main Entry Point
# ============================================================

def main():
    """Run the demo server."""
    port = int(os.environ.get("DEMO_PORT", 8000))
    logger.info("🚀 Starting Pangea Net Demo Server...")
    logger.info(f"📁 Static files: {STATIC_DIR}")
    logger.info(f"📊 Seed data: {SEED_DATA_FILE}")
    logger.info(f"🌐 Port: {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
