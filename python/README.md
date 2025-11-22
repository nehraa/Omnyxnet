# Pangea Net Python AI Component

Python AI component that monitors Go nodes and predicts network threats using 1D CNN.

## Features

- **GPU/CPU Support**: Automatically uses GPU if available, falls back to CPU
- **Peer Health Management**: Tracks healthy peers, potential IPs, and peer scores
- **Time-Series Prediction**: 1D CNN for predicting network degradation
- **Easy CLI**: Simple commands for all operations
- **Automatic Reconnection**: Reconnects to failed peers automatically

## Installation

```bash
cd python
pip install -r requirements.txt
```

## Quick Start

### Connect to Go Node
```bash
python main.py connect --host localhost --port 8080
```

### List All Nodes
```bash
python main.py list-nodes
```

### Connect to a Peer
```bash
python main.py connect-peer 2 localhost 9091
```

### Start Threat Prediction
```bash
python main.py predict --poll-interval 1.0
```

### Update Threat Score Manually
```bash
python main.py update-threat 1 0.85
```

### Check Health Status
```bash
python main.py health-status
```

## Available Commands

- `connect` - Test connection to Go node
- `list-nodes` - List all nodes
- `connect-peer <id> <host> <port>` - Connect to new peer
- `update-threat <node_id> <score>` - Update threat score
- `predict` - Start prediction loop
- `health-status` - Show peer health

## Python API Usage

```python
from src.client.go_client import GoNodeClient
from src.ai.predictor import ThreatPredictor

# Connect to Go node
client = GoNodeClient("localhost", 8080)
client.connect()

# Get all nodes
nodes = client.get_all_nodes()

# Get connection quality
quality = client.get_connection_quality(1)

# Update threat score
client.update_threat_score(1, 0.85)

# Start predictor
predictor = ThreatPredictor(client)
predictor.start()
```

## Peer Health Management

The system automatically maintains:
- **Healthy Peers List**: Peers with score above threshold
- **Potential IPs**: List of IPs for reconnection
- **Peer Scores**: Health scores for all peers (0.0-1.0)

Scores are calculated from:
- Latency (40% weight)
- Jitter (30% weight)
- Packet Loss (30% weight)

## GPU/CPU Fallback

The model automatically detects GPU availability:
- Uses CUDA if available
- Falls back to CPU if GPU not available
- No code changes needed

## Configuration

Edit `src/config.py` or use CLI options:
- `--poll-interval`: Data collection frequency
- `--window-size`: Time series window size
- `--host/--port`: Go node connection

