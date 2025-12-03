"""
AI module for Pangea Net.

Phase 1: Core ML capabilities
- CNN models for threat prediction
- Shard optimizer for CES configuration

Phase 2: Translation and Personalization
- Translation pipeline (ASR → NMT → TTS)
- Video lipsync
- Federated learning for personalized serialization
"""

# Conditional imports - torch may not be installed in minimal mode
try:
    from src.ai.cnn_model import ModelManager, LatencyPredictorCNN
    from src.ai.predictor import ThreatPredictor
    _AI_AVAILABLE = True
except ImportError:
    # Torch not installed - AI features unavailable
    ModelManager = None
    LatencyPredictorCNN = None
    ThreatPredictor = None
    _AI_AVAILABLE = False

__all__ = ['ModelManager', 'LatencyPredictorCNN', 'ThreatPredictor', '_AI_AVAILABLE']

