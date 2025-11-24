#!/bin/bash
# Download Sample Media for Phase 1 Streaming Tests
# =================================================

echo "🎥 Downloading sample media files for Phase 1 testing..."

# Create media directory
mkdir -p test_media/samples
cd test_media/samples

# Download small sample video (Big Buck Bunny - open source)
echo "📹 Downloading sample video (Big Buck Bunny 720p)..."
if ! command -v wget &> /dev/null; then
    echo "⚠️  wget not found, using curl..."
    if command -v curl &> /dev/null; then
        curl -L -o sample_video.mp4 "https://download.blender.org/demo/movies/BBB/bbb_sunflower_1080p_30fps_normal.mp4.zip"
    else
        echo "❌ Neither wget nor curl found. Creating synthetic video..."
        # We'll generate synthetic video in Python instead
        touch sample_video_placeholder.txt
    fi
else
    # Download a smaller sample video
    wget -O sample_video.mp4 "https://sample-videos.com/zip/10/mp4/SampleVideo_720x480_1mb.mp4" || {
        echo "⚠️  Video download failed, will use synthetic data"
        touch sample_video_placeholder.txt
    }
fi

# Download sample audio (Royalty-free music)
echo "🎵 Downloading sample audio..."
if command -v wget &> /dev/null; then
    wget -O sample_audio.mp3 "https://www.soundjay.com/misc/sounds-1024.mp3" || {
        echo "⚠️  Audio download failed, will generate synthetic audio"
        touch sample_audio_placeholder.txt
    }
elif command -v curl &> /dev/null; then
    curl -L -o sample_audio.mp3 "https://www.soundjay.com/misc/sounds-1024.mp3" || {
        echo "⚠️  Audio download failed, will generate synthetic audio"
        touch sample_audio_placeholder.txt
    }
else
    echo "⚠️  No download tool available, will generate synthetic audio"
    touch sample_audio_placeholder.txt
fi

# Create a simple test image for image processing tests
echo "🖼️  Creating test image..."
cat > create_test_image.py << 'EOF'
import numpy as np
from PIL import Image
import sys

try:
    # Create a colorful test image
    width, height = 640, 480
    
    # Create gradient pattern
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    X, Y = np.meshgrid(x, y)
    
    # RGB channels with different patterns
    r = (255 * (X + Y) / 2).astype(np.uint8)
    g = (255 * np.sin(np.pi * X) * np.cos(np.pi * Y)).astype(np.uint8)
    b = (255 * (1 - X) * Y).astype(np.uint8)
    
    # Combine channels
    image = np.stack([r, g, b], axis=2)
    
    # Save as PNG
    img = Image.fromarray(image)
    img.save('test_image.png')
    
    print("✅ Test image created: test_image.png")
    
except ImportError:
    print("⚠️  PIL not available, creating placeholder")
    with open('test_image_placeholder.txt', 'w') as f:
        f.write('Placeholder for test image')
EOF

python3 create_test_image.py 2>/dev/null || echo "⚠️  Python PIL not available"

# Create test data files
echo "📊 Creating test data files..."

# JSON test data (highly compressible)
cat > test_data.json << 'EOF'
{
  "streaming_test_data": {
    "metadata": {
      "version": "1.0",
      "timestamp": "2025-11-23T00:00:00Z",
      "test_type": "phase1_streaming"
    },
    "payload": {
      "repeated_pattern": "This is a test pattern that should compress very well with Brotli compression algorithm. ",
      "numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
      "nested_data": {
        "level1": {
          "level2": {
            "level3": "Deep nesting test"
          }
        }
      }
    }
  }
}
EOF

# Text file with repetitive content (good for compression testing)
echo "📝 Creating compressible text data..."
for i in {1..1000}; do
    echo "This is line $i of the test data file. It contains repetitive patterns for compression testing."
done > large_text_file.txt

# Binary test data
echo "🔢 Creating binary test data..."
python3 -c "
import os
import struct
data = os.urandom(1024*1024)  # 1MB random data
with open('random_binary_data.bin', 'wb') as f:
    f.write(data)
print('✅ 1MB random binary data created')
" 2>/dev/null || dd if=/dev/urandom of=random_binary_data.bin bs=1024 count=1024 2>/dev/null

echo ""
echo "📁 Available test media:"
ls -lh
echo ""
echo "✅ Sample media download/creation complete!"
echo "📊 Files ready for Phase 1 streaming tests"