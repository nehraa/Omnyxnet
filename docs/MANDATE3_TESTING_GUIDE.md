# Mandate 3: 50-Node Testing Guide

**Version:** 0.7.0-alpha (Mandate 3)  
**Date:** 2025-12-08  
**Status:** Architecture Complete - Testing Infrastructure Ready

---

## Prerequisites

### Required Tools
- Docker & Docker Compose (v3.8+)
- Python 3.10+
- 16GB+ RAM (for 50 containers)
- 100GB+ disk space

### Build Requirements
```bash
# Build Go node binary
cd go
go build -o bin/go-node

# Build Rust CES library (if using CES features)
cd ../rust
cargo build --release --lib

# Install Python dependencies
cd ../python
pip install -r requirements.txt
```

---

## 50-Node Deployment

### 1. Generate Full Docker Compose Configuration

```bash
# Generate complete 50-node configuration
python3 scripts/generate_50node_compose.py > docker/docker-compose.50node-full.yml

# Verify configuration
docker-compose -f docker/docker-compose.50node-full.yml config --quiet
```

### 2. Deploy the 50-Node Cluster

```bash
# Start all 50 nodes
docker-compose -f docker/docker-compose.50node-full.yml up -d

# Wait for cluster to stabilize (2-3 minutes)
sleep 180

# Check cluster status
docker-compose -f docker/docker-compose.50node-full.yml ps

# Verify network connectivity
docker network inspect wgt-mesh
```

### 3. Monitor Cluster Health

```bash
# View logs from bootstrap nodes
docker-compose -f docker/docker-compose.50node-full.yml logs -f bootstrap1 bootstrap2 bootstrap3

# View logs from aggregators
docker-compose -f docker/docker-compose.50node-full.yml logs -f aggregator1

# View logs from workers
docker-compose -f docker/docker-compose.50node-full.yml logs -f worker1 worker2 worker3
```

---

## Test 1: Tor/Proxy Communication (Mandate 3 Requirement)

**Objective:** Test communication between two arbitrary nodes using the `--use-tor` flag.

### Prerequisites
```bash
# Install Tor proxy (on host or in container)
sudo apt-get install tor

# Configure Tor SOCKS5 proxy on port 9050
# Edit /etc/tor/torrc:
SOCKSPort 9050
SOCKSPolicy accept 172.30.0.0/24
```

### Test Execution

**Step 1: Configure Proxy on Node**
```bash
# Connect to worker1
docker exec -it wgt-worker1 /bin/sh

# Set proxy configuration (via Python CLI when implemented)
# python -m src.cli proxy-config --host 172.17.0.1 --port 9050 --type socks5
```

**Step 2: Test Communication with Tor Flag**
```bash
# From worker1, ping worker20 using Tor
# python -m src.cli ping --host worker20 --port 8080 --use-tor

# Expected output:
# ✅ Ping successful via Tor proxy
# Latency: ~200-500ms (higher due to Tor routing)
# Circuit: [tor-circuit-info]
```

**Step 3: Verify Proxy Usage**
```bash
# Check Tor logs for connection
docker-compose -f docker/docker-compose.50node-full.yml logs worker1 | grep -i "socks5\|tor\|proxy"

# Expected log entries:
# [INFO] SOCKS5 connection established: 172.17.0.1:9050
# [INFO] Routing through Tor circuit: [circuit-id]
# [INFO] Message sent to worker20 via proxy
```

### Success Criteria
- ✅ Communication succeeds with `--use-tor` flag
- ✅ Logs show SOCKS5 proxy usage
- ✅ Higher latency confirms Tor routing
- ✅ No direct connection visible in network traces

---

## Test 2: Ephemeral Chat with Encryption (Mandate 3 Requirement)

**Objective:** Establish encrypted chat session between two nodes and verify end-to-end encryption.

### Test 2A: Asymmetric Encryption (RSA)

**Step 1: Start Chat Session**
```bash
# From worker1, start chat with worker10
docker exec -it wgt-worker1 sh

# Start chat session with asymmetric encryption
# python -m src.cli chat start --peer worker10:8080 --encryption asymmetric

# Expected output:
# ✅ Chat session started: session-12345
# Encryption: RSA-2048-OAEP
# Key exchange: SUCCESS
# Public key exchanged: [key-fingerprint]
```

**Step 2: Send Encrypted Messages**
```bash
# Send message from worker1
# python -m src.cli chat send --session session-12345 --message "Hello from worker1"

# Receive on worker10
docker exec -it wgt-worker10 sh
# python -m src.cli chat receive

# Expected output:
# ✅ Message received
# From: worker1
# Message: "Hello from worker1"
# Encryption: RSA-2048
# Signature: VERIFIED
```

**Step 3: Verify Encryption**
```bash
# Check logs for encryption details
docker-compose logs worker1 | grep -i "encryption\|rsa\|key"

# Expected log entries:
# [INFO] RSA key pair generated: 2048 bits
# [INFO] Public key exported: [fingerprint]
# [INFO] Message encrypted with peer public key
# [INFO] Signature created: [sig-hash]
```

### Test 2B: Symmetric Encryption (AES)

```bash
# Start chat with symmetric encryption
# python -m src.cli chat start --peer worker15:8080 --encryption symmetric

# Expected output:
# ✅ Chat session started: session-67890
# Encryption: AES-256-GCM
# Session key: [derived]
# Key exchange: Diffie-Hellman
```

### Success Criteria
- ✅ Chat session establishes successfully
- ✅ Key exchange completes
- ✅ Messages are encrypted before transmission
- ✅ Digital signatures are created and verified
- ✅ Decryption succeeds on receiving end
- ✅ Both asymmetric and symmetric modes work

---

## Test 3: Distributed ML Training (Mandate 3 Requirement)

**Objective:** Distribute dataset across 40+ workers, perform parallel training, and aggregate gradients.

### Step 1: Prepare Dataset

```bash
# Generate synthetic dataset for testing
python3 << 'EOF'
import numpy as np
import pickle

# Create synthetic training data (MNIST-like)
X_train = np.random.randn(10000, 784)  # 10k samples, 784 features
y_train = np.random.randint(0, 10, 10000)  # 10 classes

# Save dataset
with open('/tmp/ml_dataset.pkl', 'wb') as f:
    pickle.dump({'X': X_train, 'y': y_train}, f)

print("Dataset created: 10,000 samples, 784 features, 10 classes")
EOF
```

### Step 2: Distribute Dataset to Workers

```bash
# Connect to aggregator1 (coordinator)
docker exec -it wgt-aggregator1 sh

# Distribute dataset to all 40 workers
# python -m src.cli ml distribute-dataset \
#   --dataset /tmp/ml_dataset.pkl \
#   --workers worker1,worker2,...,worker40 \
#   --chunks 40

# Expected output:
# ✅ Dataset sharded into 40 chunks
# ✅ Distributing to 40 workers...
# ✅ worker1: 250 samples (chunks 0)
# ✅ worker2: 250 samples (chunks 1)
# ...
# ✅ worker40: 250 samples (chunks 39)
# ✅ Distribution complete
```

### Step 3: Start ML Training

```bash
# Start distributed training from aggregator1
# python -m src.cli ml train-start \
#   --task-id mnist-task-001 \
#   --model-arch simple-cnn \
#   --workers worker1,worker2,...,worker40 \
#   --aggregator aggregator1 \
#   --epochs 10 \
#   --batch-size 32

# Expected output:
# ✅ Training task created: mnist-task-001
# ✅ Workers initialized: 40/40
# ✅ Starting epoch 1/10...
```

### Step 4: Monitor Training Progress

```bash
# Check training status
# python -m src.cli ml status --task-id mnist-task-001

# Expected output:
# Task: mnist-task-001
# Status: RUNNING
# Current Epoch: 3/10
# Active Workers: 40/40
# Loss: 0.543 (epoch 3)
# Accuracy: 78.5% (epoch 3)
# Est. Time Remaining: 7 minutes
```

### Step 5: Verify Gradient Aggregation

```bash
# Check aggregator logs for gradient collection
docker-compose logs aggregator1 | grep -i "gradient"

# Expected log entries:
# [INFO] Gradient received from worker1: loss=0.623, samples=250
# [INFO] Gradient received from worker2: loss=0.601, samples=250
# ...
# [INFO] All 40 gradients received for epoch 1
# [INFO] Performing FedAvg aggregation...
# [INFO] Aggregated loss: 0.587, accuracy: 75.2%
# [INFO] Broadcasting model update (version 2) to 40 workers
```

### Success Criteria
- ✅ Dataset distributed to 40+ workers
- ✅ All workers start training
- ✅ Gradients collected from all workers
- ✅ FedAvg aggregation succeeds
- ✅ Model updates broadcast successfully
- ✅ Training converges (loss decreases)

---

## Test 4: Fault Tolerance (Mandate 3 Requirement)

**Objective:** Kill 5 random worker containers during training and verify graceful handling.

### Step 1: Start Training (from Test 3)

```bash
# Ensure training is running from Test 3
# python -m src.cli ml status --task-id mnist-task-001

# Expected: Status = RUNNING, Epoch 3/10
```

### Step 2: Inject Failures

```bash
# Kill 5 random worker containers
WORKERS_TO_KILL="worker5 worker12 worker23 worker31 worker38"

for worker in $WORKERS_TO_KILL; do
    echo "Killing $worker..."
    docker-compose -f docker/docker-compose.50node-full.yml kill $worker
    sleep 5
done

echo "✅ Killed 5 workers: $WORKERS_TO_KILL"
```

### Step 3: Verify Continued Operation

```bash
# Check training status
# python -m src.cli ml status --task-id mnist-task-001

# Expected output:
# Task: mnist-task-001
# Status: RUNNING (degraded)
# Current Epoch: 4/10
# Active Workers: 35/40 (5 failed)
# Loss: 0.498 (epoch 4)
# Accuracy: 81.2% (epoch 4)
# ⚠️  Workers failed: worker5, worker12, worker23, worker31, worker38
# ✅ Training continues with remaining 35 workers
```

### Step 4: Check Error Handling Logs

```bash
# Check aggregator logs for failure handling
docker-compose logs aggregator1 | grep -i "fail\|error\|timeout"

# Expected log entries:
# [WARN] Worker timeout: worker5 (no gradient in 30s)
# [WARN] Worker timeout: worker12 (no gradient in 30s)
# [INFO] Removing failed workers from active set
# [INFO] Continuing aggregation with 35/40 workers
# [INFO] Epoch 4 aggregation: 35 gradients (5 missing)
# [INFO] Model update successful despite failures
```

### Step 5: Verify Graceful Degradation

```bash
# Training should continue without crashes
# Loss and accuracy should still improve (may be slightly slower)

# Check that system didn't crash
docker-compose ps aggregator1
# Expected: State = Up

docker-compose ps | grep worker | grep Up | wc -l
# Expected: 35 (40 - 5 killed)
```

### Success Criteria
- ✅ System detects worker failures
- ✅ Training continues with remaining 35 workers
- ✅ No system crashes or panics
- ✅ Aggregator handles missing gradients gracefully
- ✅ Model updates still broadcast successfully
- ✅ Loss/accuracy continue to improve
- ✅ Error logs show proper failure handling

---

## Cleanup

```bash
# Stop all 50 nodes
docker-compose -f docker/docker-compose.50node-full.yml down

# Remove volumes (optional)
docker-compose -f docker/docker-compose.50node-full.yml down -v

# Clean up images (optional)
docker system prune -a
```

---

## Expected Test Results Summary

### Test 1: Tor Communication
| Metric | Expected Value |
|--------|----------------|
| Success Rate | 100% |
| Latency (direct) | 10-50ms |
| Latency (via Tor) | 200-500ms |
| Proxy Usage | Confirmed in logs |

### Test 2: Encrypted Chat
| Feature | Asymmetric | Symmetric |
|---------|------------|-----------|
| Key Exchange | ✅ RSA-2048 | ✅ DH/ECDH |
| Encryption | ✅ RSA-OAEP | ✅ AES-256-GCM |
| Signatures | ✅ PKCS1v15 | ✅ HMAC |
| Message Delivery | 100% | 100% |

### Test 3: Distributed ML
| Metric | Expected Value |
|--------|----------------|
| Dataset Distribution | 100% success (40/40 workers) |
| Training Start | All 40 workers |
| Gradient Collection | 100% per epoch |
| Aggregation Time | <5s per epoch |
| Model Convergence | Loss decreases, Accuracy increases |

### Test 4: Fault Tolerance
| Metric | Expected Value |
|--------|----------------|
| Failures Injected | 5 workers |
| Detection Time | <30s |
| System Stability | No crashes |
| Continued Training | 35/40 workers (87.5%) |
| Performance Impact | <15% degradation |

---

## Troubleshooting

### Issue: Containers fail to start
```bash
# Check system resources
free -h
df -h

# Increase Docker memory limit in Docker Desktop
# Settings > Resources > Memory > 16GB

# Stagger startup (start in batches)
docker-compose -f docker/docker-compose.50node-full.yml up -d bootstrap1 bootstrap2 bootstrap3
sleep 30
docker-compose -f docker/docker-compose.50node-full.yml up -d aggregator1 aggregator2 aggregator3
sleep 30
docker-compose -f docker/docker-compose.50node-full.yml up -d $(seq -f "worker%.0f" 1 20 | tr '\n' ' ')
```

### Issue: Network connectivity issues
```bash
# Verify network exists
docker network ls | grep wgt-mesh

# Check IP assignments
docker network inspect wgt-mesh

# Test connectivity between nodes
docker exec wgt-worker1 ping -c 3 172.30.0.10  # bootstrap1
```

### Issue: RPC connection failures
```bash
# Check if Cap'n Proto port is accessible
docker exec wgt-worker1 nc -zv bootstrap1 8080

# Check Go node logs
docker logs wgt-bootstrap1
```

---

## Documentation References

- [Mandate 3 Scope Analysis](../MANDATE3_SCOPE_ANALYSIS.md)
- [Architecture Documentation](ARCHITECTURE.md)
- [Security Documentation](SECURITY.md)
- [ML Training Guide](DISTRIBUTED_COMPUTE.md)
- [Docker Setup](CONTAINERIZED_TESTING.md)

---

## Notes

**Current Implementation Status:**
- ✅ 50-node Docker Compose configuration complete
- ✅ Network topology defined (172.30.0.0/24)
- ✅ Role-based node configuration (bootstrap/aggregator/worker/gui)
- ⚠️  Test scripts require full implementation of Mandate 3 features
- ⚠️  Actual Tor integration pending
- ⚠️  Chat protocol implementation pending
- ⚠️  ML tensor operations pending

**This testing guide describes the INTENDED functionality.**  
**Full implementation requires the work outlined in MANDATE3_SCOPE_ANALYSIS.md.**
