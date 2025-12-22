#!/usr/bin/env python3
"""
Test Phase 2 ML module imports and basic functionality.

This test verifies that the Phase 2 modules can be imported
and basic initialization works without loading actual ML models.
"""
import sys
from pathlib import Path

# Add python/src to path
project_root = Path(__file__).parent.parent
python_src = project_root / "python" / "src"
sys.path.insert(0, str(python_src))


def test_translation_pipeline_import():
    """Test translation pipeline module import."""
    print("Testing translation_pipeline module import...")
    try:
        from ai.translation_pipeline import (
            TranslationPipeline,
            TranslationConfig,
            ASRModule,
            NMTModule,
            TTSModule,
        )

        print("✅ Translation pipeline modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import translation_pipeline: {e}")
        return False


def test_video_lipsync_import():
    """Test video lipsync module import."""
    print("Testing video_lipsync module import...")
    try:
        from ai.video_lipsync import (
            VideoLipsync,
            LipsyncConfig,
            FaceDetector,
            LipsyncModel,
            VideoTranslationPipeline,
        )

        print("✅ Video lipsync modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import video_lipsync: {e}")
        return False


def test_federated_learning_import():
    """Test federated learning module import."""
    print("Testing federated_learning module import...")
    try:
        from ai.federated_learning import (
            P2PFederatedLearning,
            FederatedConfig,
            CustomSerializationModel,
            LocalTrainer,
            FederatedAggregator,
        )

        print("✅ Federated learning modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import federated_learning: {e}")
        return False


def test_translation_pipeline_init():
    """Test translation pipeline initialization."""
    print("\nTesting translation pipeline initialization...")
    try:
        from ai.translation_pipeline import TranslationPipeline, TranslationConfig

        config = TranslationConfig(use_gpu=False)
        pipeline = TranslationPipeline(config)

        print(f"  - Pipeline created with config: {config.asr_model_name}")
        print(f"  - Target latency: {config.latency_target_ms}ms")
        print("✅ Translation pipeline initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize translation pipeline: {e}")
        return False


def test_video_lipsync_init():
    """Test video lipsync initialization."""
    print("\nTesting video lipsync initialization...")
    try:
        from ai.video_lipsync import VideoLipsync, LipsyncConfig

        config = LipsyncConfig(use_gpu=False, video_fps=30)
        lipsync = VideoLipsync(config)

        print(f"  - Lipsync created with model: {config.model_name}")
        print(f"  - Video FPS: {config.video_fps}")
        print("✅ Video lipsync initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize video lipsync: {e}")
        return False


def test_federated_learning_init():
    """Test federated learning initialization."""
    print("\nTesting federated learning initialization...")
    try:
        from ai.federated_learning import P2PFederatedLearning, FederatedConfig

        config = FederatedConfig(use_gpu=False, local_epochs=5)
        fl_coordinator = P2PFederatedLearning(config)

        print("  - FL coordinator created")
        print(f"  - Personalization weight: {config.personalization_weight}")
        print(f"  - Max model size: {config.max_model_size_kb}KB")
        print("✅ Federated learning initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize federated learning: {e}")
        return False


def test_csm_model():
    """Test Custom Serialization Model creation."""
    print("\nTesting Custom Serialization Model...")
    try:
        from ai.federated_learning import CustomSerializationModel, FederatedConfig
        import torch

        config = FederatedConfig()
        model = CustomSerializationModel(config)

        # Test forward pass with dummy data
        dummy_input = torch.randn(4, config.input_dim)
        compressed, reconstructed = model(dummy_input)

        print(
            f"  - Model created: {config.input_dim} -> {config.latent_dim} -> {config.input_dim}"
        )
        print(f"  - Input shape: {dummy_input.shape}")
        print(f"  - Compressed shape: {compressed.shape}")
        print(f"  - Reconstructed shape: {reconstructed.shape}")
        print(f"  - Compression ratio: {model.get_compression_ratio():.2f}x")
        print("✅ CSM model tested successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to test CSM model: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("Phase 2 ML Modules Test Suite")
    print("=" * 70)
    print()

    results = []

    # Import tests
    print("=" * 70)
    print("IMPORT TESTS")
    print("=" * 70)
    results.append(test_translation_pipeline_import())
    results.append(test_video_lipsync_import())
    results.append(test_federated_learning_import())

    # Initialization tests
    print("\n" + "=" * 70)
    print("INITIALIZATION TESTS")
    print("=" * 70)
    results.append(test_translation_pipeline_init())
    results.append(test_video_lipsync_init())
    results.append(test_federated_learning_init())

    # Model tests
    print("\n" + "=" * 70)
    print("MODEL TESTS")
    print("=" * 70)
    results.append(test_csm_model())

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)

    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n❌ {total - passed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
