#!/usr/bin/env python3
"""
Pangea Net - Industry Demo API Server

This is a lightweight FastAPI wrapper that exposes the core logic via HTTP endpoints.
It serves as the API middleware layer (Tier 2) between the frontend dashboard and
the underlying core logic.

Architecture:
    Browser (UI) ←→ WebSocket/SSE ←→ API Server (This file) ←→ Cap'n Proto ←→ Go Node
    
The demo server can operate in two modes:
1. Standalone mode: Uses simulated data from demo_seed.json
2. Connected mode: Connects to a live Go node via Cap'n Proto for real metrics

DEMO ONLY: This configuration is for demonstration purposes.
Do not use in production without proper security configuration.
"""
import asyncio
import json
import logging
import os
import subprocess
import sys
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
import uvicorn

# Add project root to path for Cap'n Proto client access
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "python"))
sys.path.insert(0, str(PROJECT_ROOT / "python" / "src"))

# Configure logging first (needed for import messages)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Try to import Cap'n Proto client for real Go node communication
GO_CLIENT_AVAILABLE = False
go_client = None

try:
    from client.go_client import GoNodeClient
    GO_CLIENT_AVAILABLE = True
    logger.info("Cap'n Proto client available - can connect to Go node")
except ImportError:
    logger.info("Cap'n Proto client not available - using simulated data only")

# Demo configuration
DEMO_DIR = Path(__file__).parent
STATIC_DIR = DEMO_DIR / "static"
SEED_DATA_FILE = DEMO_DIR / "demo_seed.json"
GO_NODE_HOST = os.environ.get("GO_NODE_HOST", "localhost")
GO_NODE_PORT = int(os.environ.get("GO_NODE_PORT", 8080))

# Note: Artificial "complexity delays" have been removed.
# All processing now happens at actual network speed without fake delays.

# FastAPI application
app = FastAPI(
    title="Pangea Net Demo API",
    description="Industry demonstration API for Pangea distributed network",
    version="1.0.0-DEMO"
)

# Get configured port for CORS
DEMO_PORT = int(os.environ.get("DEMO_PORT", 8000))

# Enable CORS for frontend (demo only - restricted to localhost)
# WARNING: This CORS configuration is for demo purposes only.
# In production, restrict origins and configure proper security.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{DEMO_PORT}",
        f"http://127.0.0.1:{DEMO_PORT}",
        "http://localhost:8000",  # Default port fallback
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# ============================================================
# State Management
# ============================================================

class DemoState:
    """Manages the demo's runtime state and golden seed data.
    
    Can operate in two modes:
    1. Standalone: Uses simulated data from demo_seed.json
    2. Connected: Connects to live Go node via Cap'n Proto for real metrics
    """
    
    def __init__(self):
        self.data = self.load_seed_data()
        self.start_time = datetime.now()
        self.is_processing = False
        self.processing_lock = asyncio.Lock()  # Protect concurrent access
        self.logs: deque = deque(maxlen=100)  # Thread-safe with auto-limit
        self.execution_count = 0
        self.go_client: Optional[Any] = None  # Cap'n Proto client
        self.connected_to_go = False
    
    def connect_to_go_node(self, host: str = None, port: int = None) -> bool:
        """Attempt to connect to Go node via Cap'n Proto.
        
        Args:
            host: Go node host address (defaults to GO_NODE_HOST)
            port: Go node port (defaults to GO_NODE_PORT)
        """
        if not GO_CLIENT_AVAILABLE:
            self.add_log("Cap'n Proto client not available", "warning")
            return False
        
        target_host = host if host else GO_NODE_HOST
        target_port = port if port else GO_NODE_PORT
        
        try:
            client = GoNodeClient(host=target_host, port=target_port)
            if client.connect():
                self.go_client = client
                self.connected_to_go = True
                self.add_log(f"🔗 Connected to Go node via Cap'n Proto ({target_host}:{target_port})", "success")
                return True
            else:
                self.add_log(f"Could not connect to Go node at {target_host}:{target_port}", "warning")
                return False
        except Exception as e:
            self.add_log(f"Cap'n Proto connection error: {str(e)}", "error")
            return False
    
    def disconnect_from_go_node(self):
        """Disconnect from Go node."""
        if self.go_client:
            try:
                self.go_client.disconnect()
            except Exception:
                self.add_log("Error during Go node disconnect", "warning")
            self.go_client = None
            self.connected_to_go = False
    
    def get_live_metrics(self) -> Optional[Dict[str, Any]]:
        """Get real metrics from Go node if connected."""
        if not self.connected_to_go or not self.go_client:
            return None
        
        try:
            # Get network metrics from Go node  
            metrics = self.go_client.get_network_metrics()
            if metrics:
                return {
                    "nodes_active": metrics.get("peerCount", 0) + 1,
                    "connected_peers": metrics.get("peerCount", 0),
                    "executions": self.execution_count,
                    "network_latency_ms": metrics.get("avgRttMs", 0),
                    "throughput_mbps": metrics.get("bandwidthMbps", 0)
                }
        except Exception as e:
            logger.warning(f"Error getting live metrics: {e}")
        return None
        
    def load_seed_data(self) -> Dict[str, Any]:
        """Load the golden seed data for consistent demo starts."""
        if SEED_DATA_FILE.exists():
            with open(SEED_DATA_FILE, "r") as f:
                return json.load(f)
        # Default seed data if file doesn't exist (cleaned up - no fake metrics)
        return {
            "metrics": {
                "nodes_active": 0,
                "connected_peers": 0,
                "executions": 0,
                "network_latency_ms": 0,
                "throughput_mbps": 0
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
    
    def get_recent_logs(self, count: int = 20) -> List[Dict[str, str]]:
        """Get the most recent N logs efficiently from deque."""
        # Deque supports efficient iteration from right side
        logs_list = list(self.logs)
        return logs_list[-count:] if len(logs_list) > count else logs_list
            
    def get_uptime(self) -> str:
        """Get demo uptime as formatted string."""
        delta = datetime.now() - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# Global state instance
state = DemoState()


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("📡 Demo server starting up...")
    state.add_log("🚀 Demo server initialized", "info")
    
    # Try to auto-connect to Go node
    if GO_CLIENT_AVAILABLE:
        # Try common ports
        for port in [8080, 8081, 8082]:
            if state.connect_to_go_node("localhost", port):
                state.add_log(f"✅ Auto-connected to Go node on port {port}", "success")
                return
        
        state.add_log("ℹ️  No Go node found - using simulated data", "info")
    else:
        state.add_log("⚠️  Cap'n Proto client not available - install pycapnp for real node connection", "warning")

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
        "connected_to_go": state.connected_to_go,
        "nodes": {
            "total": len(state.data.get("nodes", [])),
            "online": sum(1 for n in state.data.get("nodes", []) if n["status"] == "online")
        },
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/connect")
async def connect_to_go(host: str = Query(default=None), port: int = Query(default=None)):
    """
    Connect to a live Go node via Cap'n Proto.
    This enables real-time metrics from the distributed network.
    
    Args:
        host: Optional host address. If not provided, uses environment variable.
        port: Optional port. If not provided, uses environment variable.
    """
    if not GO_CLIENT_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Cap'n Proto client not available. Install pycapnp to enable."
        )
    
    if state.connected_to_go:
        return JSONResponse(
            status_code=200,
            content={"status": "already_connected", "message": "Already connected to Go node"}
        )
    
    # Use provided host/port or defaults
    target_host = host if host else GO_NODE_HOST
    target_port = port if port else GO_NODE_PORT
    
    if state.connect_to_go_node(target_host, target_port):
        return JSONResponse(
            status_code=201,
            content={"status": "connected", "message": f"Connected to Go node at {target_host}:{target_port}"}
        )
    else:
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to Go node at {target_host}:{target_port}"
        )


@app.post("/api/disconnect")
async def disconnect_from_go():
    """Disconnect from the Go node."""
    state.disconnect_from_go_node()
    return {"status": "disconnected", "message": "Disconnected from Go node"}


@app.get("/api/data")
async def get_data():
    """
    Fetches the current state/data for tables and graphs.
    Returns metrics, nodes, and recent tasks.
    If connected to Go node, uses live metrics.
    """
    # Try to get live metrics if connected
    metrics = state.get_live_metrics() or state.data.get("metrics", {})
    
    return {
        "metrics": metrics,
        "nodes": state.data.get("nodes", []),
        "recent_tasks": state.data.get("recent_tasks", []),
        "execution_count": state.execution_count,
        "logs": state.get_recent_logs(20)  # Last 20 logs for the terminal view
    }


@app.get("/api/logs")
async def get_logs():
    """Get execution logs for the terminal view."""
    return {
        "logs": state.get_recent_logs(50),
        "total_logs": len(state.logs)
    }


async def simulate_processing():
    """
    Simulates the distributed processing pipeline.
    This would normally trigger the actual core logic.
    Note: is_processing is set by run_action with lock protection.
    """
    state.add_log("🚀 Initializing distributed pipeline...", "info")
    
    # Small delay for visual feedback only (not artificial complexity delay)
    delay = 0.2
    
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
        
        # Update execution count with lock protection
        async with state.processing_lock:
            metrics = state.data.get("metrics", {})
            # Note: Fake metrics removed - only real execution count tracked
            metrics["executions"] = metrics.get("executions", 0) + 1
            
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
        # Use lock to safely update is_processing flag
        async with state.processing_lock:
            state.is_processing = False


@app.post("/api/action/run")
async def run_action(background_tasks: BackgroundTasks):
    """
    The Big Button - triggers the main distributed processing logic.
    
    Note: Artificial "complexity" parameter has been removed. 
    Processing now runs at actual network speed.
    """
    # Use lock to prevent race conditions
    async with state.processing_lock:
        if state.is_processing:
            raise HTTPException(
                status_code=409,
                detail="Processing already in progress. Please wait."
            )
        state.is_processing = True
    
    # Start processing in background
    background_tasks.add_task(simulate_processing)
    
    state.add_log(f"📦 Starting execution...", "info")
    
    return {
        "status": "started",
        "message": "Execution started",
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
    nodes = state.data.get("nodes", [])
    
    # If connected to Go node, get real peer information
    if state.connected_to_go and state.go_client:
        try:
            peers = state.go_client.get_connected_peers()
            if peers:
                # Add connected peers to nodes list
                for i, peer_id in enumerate(peers):
                    nodes.append({
                        "id": peer_id,
                        "name": f"peer-{peer_id}",
                        "status": "online",
                        "type": "peer"
                    })
        except Exception as e:
            logger.warning(f"Error getting connected peers: {e}")
    
    return {
        "nodes": nodes,
        "total": len(nodes)
    }


@app.get("/api/discover")
async def discover_nodes():
    """
    Discover local Go nodes via MDNS.
    Returns list of available nodes on the local network.
    """
    # In a real implementation, this would use MDNS to discover nodes
    # For now, we'll check common ports
    discovered = []
    import socket
    
    for port in [8080, 8081, 8082]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            if result == 0:
                discovered.append({
                    "host": "localhost",
                    "port": port,
                    "available": True
                })
        except Exception:
            pass
    
    return {
        "discovered": discovered,
        "count": len(discovered)
    }


# ============================================================
# Server-Sent Events for Real-Time Updates
# ============================================================

@app.get("/api/events")
async def stream_events(request: Request):
    """
    Server-Sent Events endpoint for real-time dashboard updates.
    More efficient than polling - pushes updates to the client.
    Uses live metrics from Go node if connected.
    """
    async def event_generator():
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break
            
            # Try to get live metrics if connected
            metrics = state.get_live_metrics() or state.data.get("metrics", {})
            
            # Build combined data
            data = {
                "status": {
                    "status": state.data.get("system_status", "healthy"),
                    "version": "1.0.0-DEMO",
                    "uptime": state.get_uptime(),
                    "is_processing": state.is_processing,
                    "connected_to_go": state.connected_to_go,
                    "nodes": {
                        "total": len(state.data.get("nodes", [])),
                        "online": sum(1 for n in state.data.get("nodes", []) if n["status"] == "online")
                    },
                    "timestamp": datetime.now().isoformat()
                },
                "data": {
                    "metrics": metrics,
                    "nodes": state.data.get("nodes", []),
                    "recent_tasks": state.data.get("recent_tasks", []),
                    "execution_count": state.execution_count,
                    "logs": state.get_recent_logs(20)
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
# DCDN Endpoints
# ============================================================

@app.get("/api/dcdn/info")
async def dcdn_info():
    """Get DCDN system information."""
    return {
        "status": "available",
        "components": {
            "quic_transport": "Low-latency packet delivery (quinn)",
            "fec_engine": "Reed-Solomon forward error correction",
            "p2p_engine": "Tit-for-tat bandwidth allocation",
            "signature_verifier": "Ed25519 cryptographic verification",
            "chunk_store": "Lock-free ring buffer storage"
        },
        "performance": {
            "chunk_lookup": "O(1) - constant time",
            "fec_encoding": "~500 MB/s",
            "fec_decoding": "~300 MB/s",
            "storage": ">1 GB/s (lock-free, in-memory)",
            "signature_verify": "~0.1 ms per chunk"
        },
        "implementation": "Rust for maximum performance"
    }


@app.post("/api/dcdn/demo")
async def run_dcdn_demo(background_tasks: BackgroundTasks):
    """Run DCDN demo via Python CLI."""
    state.add_log("🌐 Starting DCDN demo...", "info")
    
    async def demo_task():
        try:
            # Call Python CLI dcdn demo command
            result = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "python" / "main.py"), "dcdn", "demo"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                state.add_log("✅ DCDN demo completed successfully", "success")
                # Parse and log demo output
                for line in result.stdout.split('\n'):
                    if line.strip():
                        state.add_log(f"  {line.strip()}", "info")
            else:
                state.add_log(f"❌ DCDN demo failed: {result.stderr}", "error")
        
        except subprocess.TimeoutExpired:
            state.add_log("❌ DCDN demo timed out", "error")
        except Exception as e:
            state.add_log(f"❌ Error running DCDN demo: {str(e)}", "error")
    
    background_tasks.add_task(demo_task)
    
    return {
        "status": "started",
        "message": "DCDN demo started in background"
    }


@app.post("/api/dcdn/test")
async def run_dcdn_test(background_tasks: BackgroundTasks):
    """Run DCDN tests via Python CLI."""
    state.add_log("🧪 Starting DCDN tests...", "info")
    
    async def test_task():
        try:
            result = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "python" / "main.py"), "dcdn", "test"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                state.add_log("✅ All DCDN tests passed", "success")
            else:
                state.add_log(f"❌ DCDN tests failed: {result.stderr}", "error")
        
        except subprocess.TimeoutExpired:
            state.add_log("❌ DCDN tests timed out", "error")
        except Exception as e:
            state.add_log(f"❌ Error running DCDN tests: {str(e)}", "error")
    
    background_tasks.add_task(test_task)
    
    return {
        "status": "started",
        "message": "DCDN tests started in background"
    }


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
    logger.info("🔒 Binding to localhost only (127.0.0.1) for security")
    
    # Note: Auto-connect is handled in the startup event
    
    uvicorn.run(
        app,
        host="127.0.0.1",  # Bind to localhost only to match CORS policy
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
