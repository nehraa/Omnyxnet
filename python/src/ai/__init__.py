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

from ai.cnn_model import ModelManager, LatencyPredictorCNN
from ai.predictor import ThreatPredictor

__all__ = ['ModelManager', 'LatencyPredictorCNN', 'ThreatPredictor']

