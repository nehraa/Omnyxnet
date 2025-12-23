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

from typing import Optional, Any

# Fallback names for runtime
ModelManager: Optional[Any] = None
LatencyPredictorCNN: Optional[Any] = None
ThreatPredictor: Optional[Any] = None

# At runtime, attempt to import concrete classes; fall back to None when unavailable
try:
    from src.ai.cnn_model import (
        ModelManager as _ModelManager,
        LatencyPredictorCNN as _LatencyPredictorCNN,
    )
    from src.ai.predictor import ThreatPredictor as _ThreatPredictor

    ModelManager = _ModelManager
    LatencyPredictorCNN = _LatencyPredictorCNN
    ThreatPredictor = _ThreatPredictor
    _AI_AVAILABLE = True
except ImportError:
    # Torch not installed - AI features unavailable
    _AI_AVAILABLE = False

__all__ = ["ModelManager", "LatencyPredictorCNN", "ThreatPredictor", "_AI_AVAILABLE"]
