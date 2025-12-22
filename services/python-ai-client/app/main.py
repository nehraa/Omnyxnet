#!/usr/bin/env python3
"""
Main entry point for Pangea Python AI Service.
Initiates connection to Go Orchestrator and starts the training loop.
"""

import logging
import os
import sys
from pathlib import Path

# Add app directory to path
APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

from app.training_core import TrainingEngine
from app.observability import ObservabilityManager, setup_metrics

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the Python AI Service."""
    logger.info("🚀 Pangea Python AI Service starting")

    # Initialize observability
    obs_manager = ObservabilityManager()
    obs_manager.initialize()

    # Start Prometheus metrics server
    metrics_port = int(os.getenv("METRICS_PORT", "8081"))
    setup_metrics(metrics_port)

    # Configuration
    orchestrator_host = os.getenv("ORCHESTRATOR_HOST", "go-orchestrator")
    orchestrator_port = int(os.getenv("ORCHESTRATOR_PORT", "8080"))
    compute_host = os.getenv("COMPUTE_HOST", "rust-compute")
    compute_port = int(os.getenv("COMPUTE_PORT", "9090"))

    logger.info(f"📡 Orchestrator: {orchestrator_host}:{orchestrator_port}")
    logger.info(f"📡 Compute Core: {compute_host}:{compute_port}")

    try:
        # Initialize training engine
        engine = TrainingEngine(
            orchestrator_addr=(orchestrator_host, orchestrator_port),
            compute_addr=(compute_host, compute_port),
            worker_id=1,
        )
        logger.info("✅ Training engine initialized")

        # Start training loop
        logger.info("🏋️  Starting training loop")
        engine.run()

    except KeyboardInterrupt:
        logger.info("⏹️  Received interrupt signal")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        obs_manager.capture_error(e)
        sys.exit(1)
    finally:
        obs_manager.shutdown()


if __name__ == "__main__":
    main()
