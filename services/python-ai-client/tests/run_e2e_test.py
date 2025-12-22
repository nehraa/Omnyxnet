#!/usr/bin/env python3
"""
End-to-end test suite for Pangea distributed training.

Tests the complete flow:
1. Data preprocessing in Rust Compute Core
2. Model training in Python AI Service
3. Gradient aggregation in Go Orchestrator
4. Distributed synchronization across services
"""

import logging
import sys
from pathlib import Path

# Setup path
TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR.parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from app.training_core import TrainingEngine

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [%(name)s] - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_training_engine_initialization():
    """Test that TrainingEngine initializes correctly."""
    logger.info("🧪 Test: TrainingEngine Initialization")

    try:
        engine = TrainingEngine(
            orchestrator_addr=("go-orchestrator", 8080),
            compute_addr=("rust-compute", 9090),
            worker_id=1,
            batch_size=32,
            epochs=2,
        )
        assert engine.worker_id == 1
        assert engine.batch_size == 32
        assert engine.epochs == 2
        logger.info("✅ Test passed: TrainingEngine initialized correctly")
        return True
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


def test_ingest_and_train_step():
    """Test single training step with data ingestion."""
    logger.info("🧪 Test: Ingest and Train Step")

    try:
        import numpy as np

        engine = TrainingEngine(
            orchestrator_addr=("go-orchestrator", 8080),
            compute_addr=("rust-compute", 9090),
            worker_id=1,
        )

        # Create dummy batch
        batch = np.random.randn(32, 10).astype(np.float32)

        # Run training step
        loss, gradients = engine.ingest_and_train_step(batch)

        assert isinstance(loss, float)
        assert gradients.shape == batch.shape
        assert loss > 0
        logger.info("✅ Test passed: Training step executed successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


def test_distributed_training_flow():
    """Test complete distributed training flow."""
    logger.info("🧪 Test: Distributed Training Flow (E2E)")

    try:
        import numpy as np

        logger.info("📍 Step 1: Initialize training engine")
        engine = TrainingEngine(
            orchestrator_addr=("go-orchestrator", 8080),
            compute_addr=("rust-compute", 9090),
            worker_id=1,
            batch_size=16,
            epochs=1,  # Just 1 epoch for testing
        )
        logger.info("✅ Engine initialized")

        logger.info("📍 Step 2: Simulate data ingestion from Rust Compute Core")
        batch = np.random.randn(16, 10).astype(np.float32)
        logger.info(f"   Input shape: {batch.shape}")

        logger.info("📍 Step 3: Execute training step")
        loss, gradients = engine.ingest_and_train_step(batch)
        logger.info(f"   Loss: {loss:.6f}")
        logger.info(f"   Gradient norm: {np.linalg.norm(gradients):.6f}")

        logger.info("📍 Step 4: Simulate gradient synchronization with orchestrator")
        engine._sync_gradients(loss, gradients)
        logger.info("   Gradient sync complete")

        logger.info("✅ Test passed: E2E distributed flow successful")
        return True
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


def run_all_tests():
    """Run all E2E tests and report results."""
    logger.info("=" * 70)
    logger.info("🧪 PANGEA DISTRIBUTED TRAINING - END-TO-END TEST SUITE")
    logger.info("=" * 70)
    logger.info("")

    tests = [
        test_training_engine_initialization,
        test_ingest_and_train_step,
        test_distributed_training_flow,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            logger.error(f"Unexpected error in test: {e}", exc_info=True)
            results.append(False)

        logger.info("")

    # Summary
    logger.info("=" * 70)
    passed = sum(results)
    total = len(results)
    logger.info(f"📊 TEST SUMMARY: {passed}/{total} tests passed")

    if passed == total:
        logger.info("✅ ALL TESTS PASSED!")
        logger.info("=" * 70)
        return 0
    else:
        logger.error(f"❌ {total - passed} test(s) failed")
        logger.info("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
