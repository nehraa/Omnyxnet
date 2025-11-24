# Phase 2: ML Translation - Quick Start Guide

**Version:** 0.5.0-alpha  
**Status:** Development  
**Last Updated:** 2024-11-24

## Overview

Phase 2 adds ML-powered translation and personalization to Pangea Net. This guide shows how to use the new features once models are integrated.

## Quick Links

- **Full Documentation**: [PHASE2_ML_IMPLEMENTATION.md](PHASE2_ML_IMPLEMENTATION.md)
- **Module Code**: `python/src/ai/`
- **Tests**: `tests/test_phase2_*.py`

## Current Status

| Feature | Status | Ready to Use |
|---------|--------|--------------|
| Translation Pipeline Structure | ✅ Complete | Module ready |
| Video Lipsync Structure | ✅ Complete | Module ready |
| Federated Learning Structure | ✅ Complete | Module ready |
| Model Integration | 🚧 In Progress | Not yet |
| End-to-End Testing | ❌ Pending | Not yet |

**Note:** Phase 2 modules are currently **framework/structure only**. ML model integration is the next step.

## Installation

### Phase 1 Dependencies (Already Installed)

```bash
cd python
source .venv/bin/activate
pip install torch>=2.0.0 numpy>=1.24.0 pycapnp>=1.0.0
```

### Phase 2 Dependencies (To Be Added)

```bash
# When ready for model integration, add:
pip install transformers>=4.30.0      # Whisper, NMT models
pip install torchaudio>=2.0.0         # Audio processing
pip install sentencepiece>=0.1.99     # Tokenization
# pip install TTS>=0.15.0             # Coqui TTS (optional, large)
# pip install opencv-python>=4.8.0    # Video processing
# pip install mediapipe>=0.10.0       # Face detection (optional)
```

## Usage Examples

### 1. Audio Translation (When Models Integrated)

```python
from src.ai.translation_pipeline import TranslationPipeline, TranslationConfig
import numpy as np

# Configure
config = TranslationConfig(
    asr_model_name="openai/whisper-tiny",
    nmt_model_name="facebook/nllb-200-distilled-600M",
    use_gpu=True,  # Auto-falls back to CPU
    latency_target_ms=150
)

# Initialize
pipeline = TranslationPipeline(config)
pipeline.load_models()  # This will load actual models when integrated

# Register speaker voice for cloning
reference_audio = np.random.randn(16000)  # 1 second @ 16kHz
voice_id = pipeline.register_voice(reference_audio, "speaker_1")

# Translate audio
input_audio = np.random.randn(48000)  # 3 seconds @ 16kHz
translated_audio, metadata = pipeline.translate_audio(
    input_audio,
    sample_rate=16000,
    source_lang="eng_Latn",
    target_lang="spa_Latn",
    voice_id=voice_id
)

# Check results
print(f"Original: {metadata['transcription']['text']}")
print(f"Translated: {metadata['translation']['translated_text']}")
print(f"Latency: {metadata.get('total_latency_ms', 0)}ms")
```

### 2. Video Translation (When Models Integrated)

```python
from src.ai.translation_pipeline import TranslationPipeline, TranslationConfig
from src.ai.video_lipsync import VideoTranslationPipeline, LipsyncConfig
import numpy as np

# Setup
translation = TranslationPipeline(TranslationConfig())
video_pipeline = VideoTranslationPipeline(translation, LipsyncConfig())

# Translate video + audio
video_frames = [np.random.randn(480, 720, 3) for _ in range(90)]  # 3 sec @ 30fps
audio_data = np.random.randn(48000)  # 3 seconds @ 16kHz

synced_frames, translated_audio, metadata = video_pipeline.translate_video(
    video_frames,
    audio_data,
    sample_rate=16000,
    source_lang="eng_Latn",
    target_lang="fra_Latn"
)

print(f"Processed {len(synced_frames)} frames")
print(f"Total latency: {metadata['total_latency_ms']}ms")
print(f"Meets target: {metadata['meets_target']}")
```

### 3. Federated Learning (Ready to Use)

```python
from src.ai.federated_learning import P2PFederatedLearning, FederatedConfig
import numpy as np

# Configure
config = FederatedConfig(
    use_gpu=True,
    local_epochs=5,
    personalization_weight=0.7,
    max_model_size_kb=50
)

# Initialize
fl_coordinator = P2PFederatedLearning(config)

# Simulate voice data (80-dim mel spectrogram features)
voice_data = [np.random.randn(80) for _ in range(100)]

# Round 1: Train locally
print("Training locally...")
metrics = fl_coordinator.train_local_round(voice_data, round_num=1)
print(f"Training loss: {metrics['avg_loss']:.6f}")
print(f"Compression ratio: {metrics['compression_ratio']:.2f}x")

# Get model for handshake
model_weights = fl_coordinator.get_model_for_handshake()
print(f"Model size: {len(model_weights) / 1024:.2f} KB")

# Simulate receiving peer models
peer_weights_1 = model_weights  # In reality, from peer 1
peer_weights_2 = model_weights  # In reality, from peer 2
peer_weights_3 = model_weights  # In reality, from peer 3

fl_coordinator.receive_peer_model("peer_1", peer_weights_1)
fl_coordinator.receive_peer_model("peer_2", peer_weights_2)
fl_coordinator.receive_peer_model("peer_3", peer_weights_3)

# Aggregate with peers
success = fl_coordinator.aggregate_with_peers()
if success:
    print("✅ Aggregation successful")
    stats = fl_coordinator.get_statistics()
    print(f"Peer models: {stats['num_peers']}")
```

## Testing

### Structure Tests (Working Now)

```bash
# Test module structure
python tests/test_phase2_structure.py

# Expected output:
# ✅ ALL STRUCTURE TESTS PASSED!
# Tests passed: 14/14
```

### Full Module Tests (Requires PyTorch)

```bash
# Install dependencies first
cd python
source .venv/bin/activate
pip install torch numpy

# Run full tests
python tests/test_phase2_modules.py
```

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Input Audio/Video                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  Translation Pipeline                        │
├─────────────────────────────────────────────────────────────┤
│  1. ASR: Transcribe audio → text + prosody                  │
│  2. NMT: Translate text → target language                   │
│  3. TTS: Synthesize with voice cloning                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  Video Lipsync (Optional)                    │
├─────────────────────────────────────────────────────────────┤
│  1. Face Detection: Find mouth region                       │
│  2. Lipsync Model: Generate new lip movements               │
│  3. Composition: Merge into original video                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              Translated Audio/Video Output                   │
└─────────────────────────────────────────────────────────────┘

Parallel Process:
┌─────────────────────────────────────────────────────────────┐
│               Federated Learning (Background)                │
├─────────────────────────────────────────────────────────────┤
│  1. Local Training: Train CSM on user voice                 │
│  2. Weight Exchange: Share during Noise handshake           │
│  3. Aggregation: Blend local + peer models                  │
│  4. Personalization: Improve compression for user           │
└─────────────────────────────────────────────────────────────┘
```

## Performance Targets

| Component | Target Latency | Notes |
|-----------|---------------|-------|
| ASR | <50ms | Per second of audio |
| NMT | <30ms | Per sentence |
| TTS | <50ms | Per sentence |
| **Audio Total** | **<150ms** | End-to-end |
| Face Detection | <5ms | Per frame |
| Lipsync | <15ms | Per frame @ 30fps |
| **Video Total** | **<50ms** | Per frame |
| **Complete Pipeline** | **<200ms** | Audio + Video |

## File Sizes

| Component | Current Size | Lines |
|-----------|--------------|-------|
| translation_pipeline.py | 17KB | 483 |
| video_lipsync.py | 16KB | 463 |
| federated_learning.py | 20KB | 553 |
| PHASE2_ML_IMPLEMENTATION.md | 19KB | 630 |

## Next Steps

### For Developers

1. **Integrate Models** (High Priority)
   ```bash
   # Add to requirements.txt:
   transformers>=4.30.0
   torchaudio>=2.0.0
   sentencepiece>=0.1.99
   ```

2. **Test Pipeline** (High Priority)
   ```bash
   python tests/test_audio_translation.py
   python tests/test_video_translation.py
   ```

3. **Optimize** (Medium Priority)
   - Model quantization (INT8/FP16)
   - Batch processing
   - GPU memory optimization

### For Users

**Current Status**: Phase 2 is in development. The module structure is complete, but ML models are not yet integrated.

**When Available**: You'll be able to:
- Translate live audio/video calls
- Preserve speaker voice characteristics
- Sync lips in video streams
- Benefit from personalized voice compression

**Timeline**: Model integration in progress. Check back for updates.

## Troubleshooting

### Import Errors

```python
# If you see: "No module named 'torch'"
cd python
source .venv/bin/activate
pip install torch>=2.0.0 numpy>=1.24.0
```

### Out of Memory

```python
# Use CPU instead of GPU
config = TranslationConfig(use_gpu=False)
```

### Model Loading Slow

```python
# Models load on first use (lazy loading)
# Subsequent calls are fast
# Or pre-load:
pipeline.load_models()  # Do once at startup
```

## Support

- **Documentation**: [PHASE2_ML_IMPLEMENTATION.md](PHASE2_ML_IMPLEMENTATION.md)
- **Issues**: https://github.com/nehraa/WGT/issues
- **Repository**: https://github.com/nehraa/WGT

## Contributing

Phase 2 is actively being developed. Contributions welcome:

1. Model integration (Whisper, NLLB-200, TTS)
2. Performance optimization
3. Testing and benchmarks
4. Documentation improvements

---

**Last Updated:** 2024-11-24  
**Maintained by:** nehraa  
**Branch:** copilot/implement-part-2-phase-1
