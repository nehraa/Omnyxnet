# Distributed Compute System - Architecture & Implementation

**Version:** 1.0.0  
**Last Updated:** 2025-12-03  
**Status:** ✅ Active

## Overview

The Distributed Compute System extends Pangea Net with a **Hierarchical Task Network** (Recursive Delegation Model) for scalable distributed computation. Instead of a star topology (one manager, many workers), this implements a tree topology where nodes can both delegate and execute work.

This system follows the **Golden Rule**:
- **Rust:** Compute Engine (WASM sandbox, verification, split/merge execution)
- **Go:** Orchestrator (network management, load balancing, task delegation)
- **Python:** Client SDK (job definition, data preprocessing, result visualization)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Distributed Compute Stack                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     Python Client SDK                                │    │
│  │  ├─→ Job Definition DSL (Split, Execute, Merge functions)          │    │
│  │  ├─→ Data Pre-processing (chunking, encoding)                      │    │
│  │  └─→ Result Visualization (graphs, models, images)                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                               ↓ Cap'n Proto RPC                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     Go Orchestrator                                  │    │
│  │  ├─→ Task Scheduling (complexity scoring, delegation decisions)     │    │
│  │  ├─→ Load Balancing (peer queries, routing)                        │    │
│  │  ├─→ State Management (chunk tracking, verification status)        │    │
│  │  └─→ Timeout/Retry Handling (fault tolerance)                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                               ↓ IPC (Shared Memory)                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     Rust Compute Engine                              │    │
│  │  ├─→ WASM Sandbox (Wasmtime runtime, resource limits)              │    │
│  │  ├─→ Verification (Merkle trees, cryptographic hashes)             │    │
│  │  └─→ Split/Merge Execution (data processing)                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Concepts

### 1. The MapReduce Interface

Every job submitted to the network must provide three functions (compiled to WASM):

```rust
/// Split: Break input data into smaller chunks
fn split(data: &[u8]) -> Vec<Vec<u8>>;

/// Execute: Perform the actual computation on a chunk
fn execute(chunk: &[u8]) -> Vec<u8>;

/// Merge: Combine multiple results into one
fn merge(results: Vec<Vec<u8>>) -> Vec<u8>;
```

### 2. Complexity Scoring

Each node calculates a `ComplexityScore` to determine if it should delegate or execute:

```
ComplexityScore = (data_size * operation_weight) / available_capacity

If Score > Threshold:
    → Node becomes MANAGER (splits and delegates)
Else:
    → Node becomes WORKER (executes directly)
```

### 3. Recursive Delegation Tree

```
                    Root Node (Task: 10,000 rows)
                           │
           ┌───────────────┼───────────────┐
           │               │               │
      Sub-Manager A   Sub-Manager B   Worker C
      (3,300 rows)    (3,300 rows)    (100 rows)
           │               │
     ┌─────┼─────┐   ┌─────┼─────┐
     │     │     │   │     │     │
   W_A1  W_A2  W_A3  W_B1  W_B2  W_B3
```

### 4. Verification Strategy

Results are verified at each delegation level:

1. **Deterministic Hash (Fast):** Manager runs same task on a small sample
2. **Redundancy (Secure):** Same chunk sent to multiple workers, results compared
3. **Merkle Proof:** Cryptographic proof of result integrity

## Data Structures

### Job Manifest

```json
{
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "wasmModule": "<base64-encoded WASM>",
  "inputData": "<base64-encoded data>",
  "complexity": {
    "dataSize": 1073741824,
    "operationType": "matrix_multiply",
    "estimatedFlops": 1e12
  },
  "config": {
    "splitStrategy": "row_based",
    "minChunkSize": 65536,
    "maxChunkSize": 1048576,
    "verificationMode": "merkle",
    "timeout": 300,
    "retryCount": 3
  },
  "routing": {
    "priority": "high",
    "locality": "prefer_local",
    "redundancy": 2
  }
}
```

### Task Packet

```json
{
  "taskId": "parent_job_id:chunk_index",
  "parentJobId": "550e8400-e29b-41d4-a716-446655440000",
  "chunkIndex": 42,
  "chunkData": "<base64-encoded chunk>",
  "wasmModuleHash": "<sha256 of wasm>",
  "expectedOutputHash": null,
  "delegationDepth": 2,
  "timeoutMs": 5000
}
```

### Task Result

```json
{
  "taskId": "parent_job_id:chunk_index",
  "status": "completed",
  "resultData": "<base64-encoded result>",
  "resultHash": "<sha256 of result>",
  "merkleProof": ["<hash1>", "<hash2>", "..."],
  "executionTimeMs": 234,
  "workerId": "12D3KooW..."
}
```

## Component Implementation

### Rust: Compute Engine

Located in `rust/src/compute/`

```
rust/src/compute/
├── mod.rs           # Module exports
├── sandbox.rs       # WASM sandbox (Wasmtime)
├── metering.rs      # Resource limiting (CPU, RAM)
├── verification.rs  # Merkle trees, hashing
├── executor.rs      # Split/Merge execution
└── types.rs         # Compute-specific types
```

**Key Features:**
- **WASM Sandbox:** Uses Wasmtime for safe, sandboxed execution
- **Resource Limits:** CPU cycle counting (metering), RAM limits
- **Zero Network Access:** WASM has no network/filesystem access
- **Parallel Execution:** Uses Rayon for parallel processing

### Go: Orchestrator

Located in `go/pkg/compute/`

```
go/pkg/compute/
├── manager.go       # Task management and delegation
├── scheduler.go     # Complexity scoring, routing
├── balancer.go      # Load balancing across peers
├── state.go         # Chunk and job state tracking
├── retry.go         # Timeout and retry logic
└── types.go         # Compute-specific types
```

**Key Features:**
- **Goroutines:** Concurrent management of many sub-workers
- **Peer Discovery:** Uses libp2p for finding compute nodes
- **State Machine:** Tracks task lifecycle (pending → assigned → computing → verifying → complete)
- **Graceful Degradation:** Falls back to local execution if network fails

### Python: Client SDK

Located in `python/src/compute/`

```
python/src/compute/
├── __init__.py      # Module exports
├── job.py           # Job definition DSL
├── preprocessor.py  # Data chunking and encoding
├── visualizer.py    # Result visualization
└── client.py        # RPC client for job submission
```

**Key Features:**
- **Pythonic API:** Easy job definition with decorators
- **Data Science Ready:** Integrates with NumPy, Pandas
- **Async Support:** Asyncio-compatible for non-blocking operations

## Protocol Flow

### Submit Job (Happy Path)

```
1. Python Client → Go Orchestrator: SubmitJob(manifest)
2. Go calculates ComplexityScore
3. IF Score > Capacity:
   a. Go → Rust: Split(data)
   b. Rust executes Split() in WASM sandbox
   c. Rust → Go: returns chunks[]
   d. Go → Peers: DelegateTask(chunk) for each chunk
   e. Peers → Go: TaskResult for each chunk
   f. Go → Rust: Merge(results[])
   g. Rust executes Merge() in WASM sandbox
   h. Rust → Go: returns final_result
4. ELSE:
   a. Go → Rust: Execute(data)
   b. Rust executes Execute() in WASM sandbox
   c. Rust → Go: returns result
5. Go → Python Client: JobResult(final_result)
```

### Verification Flow

```
1. Worker completes task, returns result + hash
2. Manager checks:
   a. Hash matches expected (if provided)?
   b. Redundant result available for comparison?
   c. Sample verification passes?
3. IF verification fails:
   a. Retry with different worker
   b. OR mark worker as untrusted
4. IF verification passes:
   a. Add to merge queue
   b. Update worker trust score
```

## Cap'n Proto Schema Extensions

Add to `go/schema/schema.capnp`:

```capnp
# Distributed Compute Types

struct ComputeJobManifest {
    jobId @0 :Text;
    wasmModule @1 :Data;
    inputData @2 :Data;
    splitStrategy @3 :Text;
    minChunkSize @4 :UInt64;
    maxChunkSize @5 :UInt64;
    verificationMode @6 :Text;
    timeoutSecs @7 :UInt32;
    retryCount @8 :UInt32;
    priority @9 :Text;
    redundancy @10 :UInt32;
}

struct ComputeTaskPacket {
    taskId @0 :Text;
    parentJobId @1 :Text;
    chunkIndex @2 :UInt32;
    chunkData @3 :Data;
    wasmModuleHash @4 :Text;
    delegationDepth @5 :UInt32;
    timeoutMs @6 :UInt32;
}

struct ComputeTaskResult {
    taskId @0 :Text;
    status @1 :Text;
    resultData @2 :Data;
    resultHash @3 :Text;
    merkleProof @4 :List(Text);
    executionTimeMs @5 :UInt64;
    workerId @6 :Text;
}

struct ComputeJobStatus {
    jobId @0 :Text;
    status @1 :Text;
    progress @2 :Float32;
    completedChunks @3 :UInt32;
    totalChunks @4 :UInt32;
    estimatedTimeRemaining @5 :UInt32;
}

interface ComputeService {
    # Submit a new compute job
    submitJob @0 (manifest :ComputeJobManifest) -> (jobId :Text, success :Bool, errorMsg :Text);
    
    # Get job status
    getJobStatus @1 (jobId :Text) -> (status :ComputeJobStatus);
    
    # Get job result (blocks until complete or timeout)
    getJobResult @2 (jobId :Text, timeoutMs :UInt32) -> (result :Data, success :Bool, errorMsg :Text);
    
    # Cancel a running job
    cancelJob @3 (jobId :Text) -> (success :Bool);
    
    # Get node compute capacity
    getComputeCapacity @4 () -> (cpuCores :UInt32, ramMb :UInt64, currentLoad :Float32);
    
    # Delegate a task to this node (internal use)
    delegateTask @5 (task :ComputeTaskPacket) -> (accepted :Bool, estimatedTimeMs :UInt32);
    
    # Return task result to delegator (internal use)
    returnTaskResult @6 (result :ComputeTaskResult) -> (verified :Bool);
}
```

## Testing

### Unit Tests

```bash
# Rust compute engine tests
cd rust && cargo test compute

# Go orchestrator tests
cd go && go test ./pkg/compute/...

# Python SDK tests
cd python && pytest tests/test_compute.py
```

### Integration Tests

```bash
# Run full compute pipeline test
./tests/test_compute_integration.sh

# Multi-node compute test
./tests/test_compute_multinode.sh
```

### Example Test Job

```python
from pangea.compute import Job, submit_job

# Define a simple computation
@Job.define
def word_count():
    @Job.split
    def split(data: bytes) -> list[bytes]:
        text = data.decode('utf-8')
        lines = text.split('\n')
        return [line.encode() for line in lines]
    
    @Job.execute
    def execute(chunk: bytes) -> bytes:
        words = chunk.decode('utf-8').split()
        count = len(words)
        return str(count).encode()
    
    @Job.merge
    def merge(results: list[bytes]) -> bytes:
        total = sum(int(r.decode()) for r in results)
        return str(total).encode()

# Submit job
result = submit_job(word_count, input_data=large_text_file)
print(f"Word count: {result.decode()}")
```

## Performance Considerations

### Resource Limits

| Resource | Default Limit | Configurable |
|----------|--------------|--------------|
| CPU Cycles | 1 billion | Yes |
| Memory | 256 MB | Yes |
| Execution Time | 30 seconds | Yes |
| Stack Size | 1 MB | No |

### Optimization Tips

1. **Chunk Size:** Balance between parallelism and overhead
2. **Verification Mode:** Use `merkle` for large results, `hash` for small
3. **Locality:** Prefer `prefer_local` for data-heavy tasks
4. **Redundancy:** Use `1` for trusted networks, `2-3` for untrusted

## Security Model

### Sandbox Guarantees

- **No Network Access:** WASM cannot make network calls
- **No File System:** WASM cannot access disk
- **Memory Isolation:** Each task runs in isolated memory
- **CPU Metering:** Prevents infinite loops

### Trust Model

- **Zero Trust:** Assume all workers are potentially malicious
- **Verification:** All results are verified before acceptance
- **Redundancy:** Critical tasks run on multiple workers
- **Reputation:** Workers build trust score over time

### Security Audit Results (v0.6.0)

**Race Conditions Fixed:**
- ✅ Go `executeChunk`: Uses mutex for state access
- ✅ Go `delegateJob`: Proper goroutine closure captures
- ✅ Python Job DSL: Thread-local storage for builder state

**Resource Limits:**
- ✅ CPU cycle metering with configurable limits
- ✅ Memory allocation tracking
- ✅ Execution time limits with interrupt capability

**Input Validation:**
- ✅ Job manifest validation before execution
- ✅ WASM module size limits
- ✅ Chunk size constraints (min/max)

**Known Limitations:**
- ⚠️ Current sandbox uses simulation mode (Wasmtime integration pending)
- ⚠️ No secure key exchange between workers (future enhancement)

## Future Enhancements

- [ ] GPU compute support (WebGPU in WASM)
- [ ] Persistent workers (keep WASM loaded between tasks)
- [ ] Task priority queues
- [ ] Cost accounting and billing
- [ ] Cross-datacenter routing
- [ ] AI-powered load prediction

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Overall system architecture
- [RUST.md](RUST.md) - Rust implementation details
- [COMMUNICATION.md](COMMUNICATION.md) - P2P networking
- [GOLDEN_RULE_UPDATE.md](GOLDEN_RULE_UPDATE.md) - Language responsibilities

---

*Last Updated: 2025-12-03*
