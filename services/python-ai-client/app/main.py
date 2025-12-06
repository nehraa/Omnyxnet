#!/usr/bin/env python3
"""
Main entry point for Pangea Python AI Service.
Initiates connection to Go Orchestrator and starts the training loop.
"""

import logging
import sys
import time
from pathlib import Path

# Add app directory to path
APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

from app.training_core import TrainingEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the Python AI Service."""
    logger.info("🚀 Pangea Python AI Service starting")
    
    # Configuration
    orchestrator_host = "go-orchestrator"
    orchestrator_port = 8080
    compute_host = "rust-compute"
    compute_port = 9090
    
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
        sys.exit(1)


if __name__ == '__main__':
    main()
