# Pangea Net - Mechanical Blueprint Architecture

This is a comprehensive "Mechanical Blueprint" diagram showing the entire Pangea Net architecture with visual metaphors representing the data flow, components, and wiring.

## Visual Metaphors Legend

- **🎛️ Control Deck** (Rounded): Main execution entry points and CLI interfaces
- **🗜️ Compression Funnel** (Trapezoid): Data ingestion and compression logic
- **🔐 Encryption Chamber** (Rectangle with thick border): Security and encryption logic
- **🚇 Tor Tunnel** (Cylinder): Proxy and network wiring
- **⚙️ Compute Engine** (Hexagon): Processing and computation
- **🗄️ Storage Vault** (Database): Data storage and caching
- **🤖 AI Brain** (Stadium): Machine learning and AI components
- **📡 Network Bridge** (Double Circle): Network adapters and protocols

## Mermaid Diagram

```mermaid
flowchart TD
    %% ========================================
    %% ENTRY POINTS - Control Decks
    %% ========================================
    DESKTOP_KIVY([🎛️ Desktop App<br/>KivyMD GUI])
    DESKTOP_TK([🎛️ Desktop App<br/>Tkinter GUI])
    PYTHON_CLI([🎛️ Python CLI<br/>Command Interface])
    GO_MAIN([🎛️ Go Node Main<br/>Entry Point])
    RUST_MAIN([🎛️ Rust Node Main<br/>Entry Point])
    
    %% ========================================
    %% PYTHON AI/ML LAYER - AI Brains
    %% ========================================
    AI_PREDICTOR{{🤖 Threat Predictor<br/>CNN Model}}
    AI_SHARD{{🤖 Shard Optimizer<br/>ML-based CES}}
    AI_TRANSLATION{{🤖 Translation Pipeline<br/>ASR → NMT → TTS}}
    AI_LIPSYNC{{🤖 Video Lipsync<br/>AV Sync}}
    AI_FEDERATED{{🤖 Federated Learning<br/>P2P-FL & CSM}}
    
    %% ========================================
    %% GO ORCHESTRATOR - Core Services
    %% ========================================
    GO_CAPNP[[📡 Cap'n Proto RPC<br/>IPC Service]]
    GO_LIBP2P[[📡 LibP2P Network<br/>NAT Traversal]]
    GO_SECURITY[🔐 Security Manager<br/>Encryption & Keys]
    GO_STREAMING[[📡 Streaming Service<br/>Video/Audio/Chat]]
    GO_COMPUTE_MGR{{⚙️ Compute Manager<br/>Task Scheduler}}
    GO_SHARED_MEM[(🗄️ Shared Memory<br/>Go↔Python IPC)]
    GO_CONFIG[(🗄️ Config Manager<br/>Persistence)]
    GO_ML_COORD{{⚙️ ML Coordinator<br/>Distributed ML}}
    
    %% ========================================
    %% RUST PERFORMANCE LAYER - Compression & Encryption
    %% ========================================
    RUST_CES[/🗜️ CES Pipeline<br/>Compression Engine\]
    RUST_ENCRYPTION[🔐 XChaCha20Poly1305<br/>Encryption Chamber]
    RUST_CODECS[/🗜️ Media Codecs<br/>Opus/Brotli\]
    RUST_UPLOAD{{⚙️ Upload Protocol<br/>CES + Transport}}
    RUST_DOWNLOAD{{⚙️ Download Protocol<br/>CES + Reconstruct}}
    RUST_FFI[[📡 FFI Bridge<br/>Go ↔ Rust]]
    RUST_CACHE[(🗄️ File Cache<br/>Manifest Store)]
    
    %% ========================================
    %% DCDN LAYER - Content Delivery
    %% ========================================
    DCDN_QUIC[[📡 QUIC Transport<br/>Low-Latency UDP]]
    DCDN_FEC{{⚙️ FEC Engine<br/>Reed-Solomon}}
    DCDN_P2P[[📡 P2P Engine<br/>Mesh Network]]
    DCDN_STORAGE[(🗄️ Chunk Store<br/>Ring Buffer)]
    DCDN_VERIFIER[🔐 Signature Verifier<br/>Ed25519 Auth]
    
    %% ========================================
    %% COMPUTE SYSTEM - Processing
    %% ========================================
    RUST_COMPUTE_SANDBOX{{⚙️ WASM Sandbox<br/>Secure Execution}}
    RUST_COMPUTE_EXEC{{⚙️ Task Executor<br/>MapReduce}}
    RUST_COMPUTE_VERIFY[🔐 Merkle Verifier<br/>Result Integrity]
    RUST_COMPUTE_METER{{⚙️ Resource Metering<br/>CPU/Memory Limits}}
    
    %% ========================================
    %% PYTHON CLIENT LAYER - Interfaces
    %% ========================================
    PYTHON_GO_CLIENT[[📡 Go RPC Client<br/>Cap'n Proto]]
    PYTHON_COMPUTE_CLIENT[[📡 Compute Client<br/>Job Management]]
    PYTHON_PREPROCESSOR[/🗜️ Data Preprocessor<br/>Input Preparation\]
    
    %% ========================================
    %% SERVICES - Microservices
    %% ========================================
    SERVICE_GO_ORCH([🎛️ Go Orchestrator<br/>Service Entry])
    SERVICE_PYTHON_AI([🎛️ Python AI Client<br/>Service Entry])
    SERVICE_RUST_COMPUTE([🎛️ Rust Compute<br/>Service Entry])
    
    %% ========================================
    %% NETWORKING - Tor Tunnels & Proxies
    %% ========================================
    GO_PROXY[(🚇 SOCKS5/Tor Proxy<br/>Anonymous Routing)]
    GO_NETWORK_ADAPTER[[📡 Network Adapter<br/>Multi-Protocol]]
    GO_DHT[[📡 DHT Discovery<br/>Peer Routing]]
    RUST_DHT[[📡 Rust DHT<br/>Content Routing)]
    
    %% ========================================
    %% STORAGE & PERSISTENCE
    %% ========================================
    GO_NODE_STORE[(🗄️ Node Store<br/>Peer Database)]
    
    %% ========================================
    %% COMMUNICATION LAYER
    %% ========================================
    PYTHON_COMM_CHAT{{📡 Live Chat<br/>P2P Messaging}}
    PYTHON_COMM_VIDEO{{📡 Live Video<br/>UDP Streaming}}
    PYTHON_COMM_VOICE{{📡 Live Voice<br/>Audio Streaming}}
    
    %% ========================================
    %% WIRING - Solid arrows for working connections
    %% ========================================
    
    %% Entry Points to Core Services
    DESKTOP_KIVY --> PYTHON_GO_CLIENT
    DESKTOP_TK --> PYTHON_GO_CLIENT
    PYTHON_CLI --> PYTHON_GO_CLIENT
    PYTHON_CLI --> PYTHON_COMPUTE_CLIENT
    
    %% Python to Go RPC Bridge
    PYTHON_GO_CLIENT --> GO_CAPNP
    PYTHON_COMPUTE_CLIENT --> GO_CAPNP
    
    %% Go Main Orchestration
    GO_MAIN --> GO_CAPNP
    GO_MAIN --> GO_LIBP2P
    GO_MAIN --> GO_NODE_STORE
    GO_MAIN --> GO_CONFIG
    GO_MAIN --> GO_SHARED_MEM
    
    %% Go to Rust FFI Bridge
    GO_CAPNP --> RUST_FFI
    RUST_FFI --> RUST_CES
    RUST_FFI --> RUST_UPLOAD
    RUST_FFI --> RUST_DOWNLOAD
    
    %% CES Pipeline Flow (Compression → Encryption → Sharding)
    RUST_CES --> RUST_CODECS
    RUST_CODECS --> RUST_ENCRYPTION
    RUST_ENCRYPTION --> RUST_UPLOAD
    RUST_UPLOAD --> RUST_CACHE
    
    %% Download Flow (Retrieval → Decryption → Decompression)
    RUST_DOWNLOAD --> RUST_CACHE
    RUST_CACHE --> RUST_ENCRYPTION
    RUST_ENCRYPTION --> RUST_CODECS
    
    %% DCDN Architecture
    RUST_MAIN --> DCDN_QUIC
    DCDN_QUIC --> DCDN_FEC
    DCDN_FEC --> DCDN_STORAGE
    DCDN_STORAGE --> DCDN_P2P
    DCDN_P2P --> DCDN_VERIFIER
    
    %% Compute System
    GO_COMPUTE_MGR --> RUST_COMPUTE_EXEC
    RUST_COMPUTE_EXEC --> RUST_COMPUTE_SANDBOX
    RUST_COMPUTE_SANDBOX --> RUST_COMPUTE_METER
    RUST_COMPUTE_EXEC --> RUST_COMPUTE_VERIFY
    
    %% Networking & Security
    GO_LIBP2P --> GO_NETWORK_ADAPTER
    GO_NETWORK_ADAPTER --> GO_PROXY
    GO_LIBP2P --> GO_DHT
    GO_SECURITY --> GO_CAPNP
    GO_STREAMING --> GO_LIBP2P
    
    %% Python AI Integration
    PYTHON_GO_CLIENT --> AI_PREDICTOR
    PYTHON_GO_CLIENT --> AI_SHARD
    PYTHON_PREPROCESSOR --> AI_TRANSLATION
    AI_TRANSLATION --> AI_LIPSYNC
    AI_FEDERATED --> GO_ML_COORD
    GO_ML_COORD --> GO_COMPUTE_MGR
    
    %% Communication Layer
    PYTHON_CLI --> PYTHON_COMM_CHAT
    PYTHON_CLI --> PYTHON_COMM_VIDEO
    PYTHON_CLI --> PYTHON_COMM_VOICE
    PYTHON_COMM_CHAT --> GO_STREAMING
    PYTHON_COMM_VIDEO --> GO_STREAMING
    PYTHON_COMM_VOICE --> GO_STREAMING
    
    %% Services Architecture
    SERVICE_GO_ORCH --> GO_CAPNP
    SERVICE_PYTHON_AI --> PYTHON_GO_CLIENT
    SERVICE_RUST_COMPUTE --> RUST_COMPUTE_EXEC
    
    %% Data Flow Connections
    RUST_UPLOAD --> GO_NETWORK_ADAPTER
    GO_NETWORK_ADAPTER --> GO_LIBP2P
    GO_LIBP2P --> DCDN_P2P
    
    RUST_DHT --> RUST_CACHE
    GO_DHT --> GO_NODE_STORE
    
    %% Python Preprocessing
    PYTHON_PREPROCESSOR --> RUST_CES
    
    %% ========================================
    %% MISSING/INCOMPLETE WIRING - Dotted red arrows
    %% ========================================
    
    %% Note: Based on analysis, all major components are wired.
    %% The following are architectural connections that could be enhanced:
    
    RUST_DHT -.->|Future: Direct DHT| DCDN_P2P
    AI_SHARD -.->|Future: ML Optimization| RUST_CES
    GO_PROXY -.->|Optional: Tor Integration| GO_NETWORK_ADAPTER
    
    %% ========================================
    %% STYLING - Visual Blueprint Aesthetics
    %% ========================================
    
    %% Control Decks (Entry Points) - Cyan
    style DESKTOP_KIVY fill:#00bcd4,stroke:#006064,stroke-width:3px,color:#fff
    style DESKTOP_TK fill:#00bcd4,stroke:#006064,stroke-width:3px,color:#fff
    style PYTHON_CLI fill:#00bcd4,stroke:#006064,stroke-width:3px,color:#fff
    style GO_MAIN fill:#00bcd4,stroke:#006064,stroke-width:3px,color:#fff
    style RUST_MAIN fill:#00bcd4,stroke:#006064,stroke-width:3px,color:#fff
    
    %% Compression Funnels - Orange
    style RUST_CES fill:#ff9800,stroke:#e65100,stroke-width:4px,color:#000
    style RUST_CODECS fill:#ff9800,stroke:#e65100,stroke-width:4px,color:#000
    style PYTHON_PREPROCESSOR fill:#ff9800,stroke:#e65100,stroke-width:3px,color:#000
    
    %% Encryption Chambers - Yellow with thick borders
    style RUST_ENCRYPTION fill:#ffeb3b,stroke:#f57f17,stroke-width:5px,color:#000
    style GO_SECURITY fill:#ffeb3b,stroke:#f57f17,stroke-width:5px,color:#000
    style DCDN_VERIFIER fill:#ffeb3b,stroke:#f57f17,stroke-width:5px,color:#000
    style RUST_COMPUTE_VERIFY fill:#ffeb3b,stroke:#f57f17,stroke-width:5px,color:#000
    
    %% Tor Tunnels (Proxies) - Purple
    style GO_PROXY fill:#9c27b0,stroke:#4a148c,stroke-width:4px,color:#fff
    
    %% Compute Engines - Red
    style GO_COMPUTE_MGR fill:#f44336,stroke:#b71c1c,stroke-width:3px,color:#fff
    style RUST_UPLOAD fill:#f44336,stroke:#b71c1c,stroke-width:3px,color:#fff
    style RUST_DOWNLOAD fill:#f44336,stroke:#b71c1c,stroke-width:3px,color:#fff
    style RUST_COMPUTE_EXEC fill:#f44336,stroke:#b71c1c,stroke-width:3px,color:#fff
    style RUST_COMPUTE_SANDBOX fill:#f44336,stroke:#b71c1c,stroke-width:3px,color:#fff
    style RUST_COMPUTE_METER fill:#f44336,stroke:#b71c1c,stroke-width:3px,color:#fff
    style DCDN_FEC fill:#f44336,stroke:#b71c1c,stroke-width:3px,color:#fff
    style GO_ML_COORD fill:#f44336,stroke:#b71c1c,stroke-width:3px,color:#fff
    
    %% Storage Vaults - Green
    style GO_SHARED_MEM fill:#4caf50,stroke:#1b5e20,stroke-width:3px,color:#fff
    style GO_CONFIG fill:#4caf50,stroke:#1b5e20,stroke-width:3px,color:#fff
    style GO_NODE_STORE fill:#4caf50,stroke:#1b5e20,stroke-width:3px,color:#fff
    style RUST_CACHE fill:#4caf50,stroke:#1b5e20,stroke-width:3px,color:#fff
    style DCDN_STORAGE fill:#4caf50,stroke:#1b5e20,stroke-width:3px,color:#fff
    
    %% AI Brains - Pink
    style AI_PREDICTOR fill:#e91e63,stroke:#880e4f,stroke-width:3px,color:#fff
    style AI_SHARD fill:#e91e63,stroke:#880e4f,stroke-width:3px,color:#fff
    style AI_TRANSLATION fill:#e91e63,stroke:#880e4f,stroke-width:3px,color:#fff
    style AI_LIPSYNC fill:#e91e63,stroke:#880e4f,stroke-width:3px,color:#fff
    style AI_FEDERATED fill:#e91e63,stroke:#880e4f,stroke-width:3px,color:#fff
    
    %% Network Bridges - Blue
    style GO_CAPNP fill:#2196f3,stroke:#0d47a1,stroke-width:3px,color:#fff
    style GO_LIBP2P fill:#2196f3,stroke:#0d47a1,stroke-width:3px,color:#fff
    style GO_STREAMING fill:#2196f3,stroke:#0d47a1,stroke-width:3px,color:#fff
    style GO_NETWORK_ADAPTER fill:#2196f3,stroke:#0d47a1,stroke-width:3px,color:#fff
    style GO_DHT fill:#2196f3,stroke:#0d47a1,stroke-width:3px,color:#fff
    style RUST_FFI fill:#2196f3,stroke:#0d47a1,stroke-width:3px,color:#fff
    style DCDN_QUIC fill:#2196f3,stroke:#0d47a1,stroke-width:3px,color:#fff
    style DCDN_P2P fill:#2196f3,stroke:#0d47a1,stroke-width:3px,color:#fff
    style RUST_DHT fill:#2196f3,stroke:#0d47a1,stroke-width:3px,color:#fff
    style PYTHON_GO_CLIENT fill:#2196f3,stroke:#0d47a1,stroke-width:3px,color:#fff
    style PYTHON_COMPUTE_CLIENT fill:#2196f3,stroke:#0d47a1,stroke-width:3px,color:#fff
    style PYTHON_COMM_CHAT fill:#2196f3,stroke:#0d47a1,stroke-width:3px,color:#fff
    style PYTHON_COMM_VIDEO fill:#2196f3,stroke:#0d47a1,stroke-width:3px,color:#fff
    style PYTHON_COMM_VOICE fill:#2196f3,stroke:#0d47a1,stroke-width:3px,color:#fff
    
    %% Services - Teal
    style SERVICE_GO_ORCH fill:#009688,stroke:#004d40,stroke-width:3px,color:#fff
    style SERVICE_PYTHON_AI fill:#009688,stroke:#004d40,stroke-width:3px,color:#fff
    style SERVICE_RUST_COMPUTE fill:#009688,stroke:#004d40,stroke-width:3px,color:#fff
    
    %% ========================================
    %% CLICKABLE LINKS TO SOURCE FILES
    %% ========================================
    
    click DESKTOP_KIVY "./desktop_app_kivy.py"
    click DESKTOP_TK "./desktop_app.py"
    click PYTHON_CLI "./python/main.py"
    click GO_MAIN "./go/main.go"
    click RUST_MAIN "./rust/src/main.rs"
    
    click AI_PREDICTOR "./python/src/ai/predictor.py"
    click AI_SHARD "./python/src/ai/shard_optimizer.py"
    click AI_TRANSLATION "./python/src/ai/translation_pipeline.py"
    click AI_LIPSYNC "./python/src/ai/video_lipsync.py"
    click AI_FEDERATED "./python/src/ai/federated_learning.py"
    
    click GO_CAPNP "./go/capnp_service.go"
    click GO_LIBP2P "./go/libp2p_node.go"
    click GO_SECURITY "./go/security.go"
    click GO_STREAMING "./go/streaming.go"
    click GO_COMPUTE_MGR "./go/pkg/compute/manager.go"
    click GO_SHARED_MEM "./go/shared_memory.go"
    click GO_CONFIG "./go/config.go"
    click GO_ML_COORD "./go/ml_coordinator.go"
    click GO_PROXY "./go/security.go"
    click GO_NETWORK_ADAPTER "./go/network_adapter.go"
    click GO_DHT "./go/libp2p_node.go"
    click GO_NODE_STORE "./go/types.go"
    
    click RUST_CES "./rust/src/ces.rs"
    click RUST_ENCRYPTION "./rust/src/ces.rs"
    click RUST_CODECS "./rust/src/codecs.rs"
    click RUST_UPLOAD "./rust/src/upload.rs"
    click RUST_DOWNLOAD "./rust/src/download.rs"
    click RUST_FFI "./rust/src/ffi.rs"
    click RUST_CACHE "./rust/src/cache.rs"
    click RUST_DHT "./rust/src/dht.rs"
    
    click DCDN_QUIC "./rust/src/dcdn/transport.rs"
    click DCDN_FEC "./rust/src/dcdn/fec.rs"
    click DCDN_P2P "./rust/src/dcdn/p2p.rs"
    click DCDN_STORAGE "./rust/src/dcdn/storage.rs"
    click DCDN_VERIFIER "./rust/src/dcdn/verifier.rs"
    
    click RUST_COMPUTE_SANDBOX "./rust/src/compute/sandbox.rs"
    click RUST_COMPUTE_EXEC "./rust/src/compute/executor.rs"
    click RUST_COMPUTE_VERIFY "./rust/src/compute/verification.rs"
    click RUST_COMPUTE_METER "./rust/src/compute/metering.rs"
    
    click PYTHON_GO_CLIENT "./python/src/client/go_client.py"
    click PYTHON_COMPUTE_CLIENT "./python/src/compute/client.py"
    click PYTHON_PREPROCESSOR "./python/src/compute/preprocessor.py"
    
    click PYTHON_COMM_CHAT "./python/src/communication/live_chat.py"
    click PYTHON_COMM_VIDEO "./python/src/communication/live_video.py"
    click PYTHON_COMM_VOICE "./python/src/communication/live_voice.py"
    
    click SERVICE_GO_ORCH "./services/go-orchestrator/main.go"
    click SERVICE_PYTHON_AI "./services/python-ai-client/app/main.py"
    click SERVICE_RUST_COMPUTE "./services/rust-compute/src/main.rs"
```

## Key Data Flows

### 1. **File Upload Flow** (Compression → Encryption → Sharding)
```
User Input → Python CLI → Go RPC → Rust CES Pipeline
  ↓
Brotli Compression (Rust Codecs)
  ↓
XChaCha20Poly1305 Encryption (Rust Encryption Chamber)
  ↓
Reed-Solomon Sharding (CES)
  ↓
Upload Protocol → Go Network Adapter → LibP2P → DCDN P2P Mesh
```

### 2. **File Download Flow** (Retrieval → Decryption → Decompression)
```
Python CLI → Go RPC → Rust Download Protocol
  ↓
DCDN P2P Mesh → LibP2P → Go Network Adapter
  ↓
Shard Retrieval from Cache/Network
  ↓
Reed-Solomon Reconstruction (CES)
  ↓
XChaCha20Poly1305 Decryption
  ↓
Brotli Decompression → Original File
```

### 3. **Distributed Compute Flow**
```
Python SDK (@task decorator) → Compute Client → Go RPC
  ↓
Compute Manager → Task Scheduler
  ↓
Rust Compute Executor → WASM Sandbox (resource limits)
  ↓
MapReduce Execution (Split/Execute/Merge)
  ↓
Merkle Tree Verification → Results back to Python
```

### 4. **Streaming Flow** (Real-time Communication)
```
Desktop App → Python Communication Layer → Go Streaming Service
  ↓
UDP/QUIC Transport (LibP2P)
  ↓
Opus Audio Codec (Rust) / Video Codecs
  ↓
P2P Direct Connection (NAT traversal via LibP2P)
```

### 5. **AI/ML Pipeline**
```
Data Input → Python Preprocessor → AI Models
  ↓
(Threat Predictor, Shard Optimizer, Translation, Lipsync, Federated Learning)
  ↓
ML Coordinator (Go) → Distributed Compute System
  ↓
Results aggregation and verification
```

## Architecture Highlights

### ✅ **Working Components** (Solid Arrows)
- **Desktop GUI** → Python RPC → Go Orchestrator
- **Python CLI** → Go Cap'n Proto RPC
- **Go** ↔ **Rust** FFI Bridge (CES operations)
- **CES Pipeline**: Compression → Encryption → Sharding
- **Upload/Download**: Full working implementation with caching
- **LibP2P**: NAT traversal, DHT discovery, peer routing
- **DCDN**: QUIC transport, FEC, P2P mesh, signature verification
- **Compute System**: WASM sandbox, Merkle verification, resource metering
- **Streaming**: Video/Audio/Chat over UDP/TCP

### ⚠️ **Future Enhancements** (Dotted Red Arrows)
- Direct Rust DHT to DCDN P2P integration (currently goes through Go)
- AI-based ML optimization for CES pipeline (model exists, not integrated)
- Full Tor proxy integration (proxy config exists, optional feature)

## Component Descriptions

### 🎛️ **Control Deck** (Entry Points)
- **Desktop Apps**: KivyMD and Tkinter GUIs for user interaction
- **Python CLI**: Command-line interface for all operations
- **Go/Rust Mains**: Service entry points for orchestration

### 🗜️ **Compression Funnel** (Data Ingestion)
- **CES Pipeline**: Compression-Encryption-Sharding in Rust
- **Media Codecs**: Opus audio, Brotli compression
- **Preprocessor**: Data preparation for AI/ML

### 🔐 **Encryption Chamber** (Security)
- **XChaCha20Poly1305**: Authenticated encryption in Rust
- **Security Manager**: Key management, proxy config in Go
- **Signature Verifier**: Ed25519 for content authenticity (DCDN)
- **Merkle Verifier**: Cryptographic result integrity (Compute)

### 🚇 **Tor Tunnel** (Network Proxy)
- **SOCKS5 Proxy**: Anonymous routing configuration in Go
- **Network Adapter**: Multi-protocol transport abstraction

### ⚙️ **Compute Engine** (Processing)
- **Compute Manager**: Task scheduling and delegation (Go)
- **Upload/Download Protocols**: File transfer with CES (Rust)
- **WASM Sandbox**: Secure computation with resource limits (Rust)
- **FEC Engine**: Forward Error Correction with Reed-Solomon (DCDN)

### 🗄️ **Storage Vault** (Persistence)
- **Shared Memory**: Go ↔ Python IPC for streaming data
- **Config Manager**: Node configuration persistence
- **Node Store**: Peer database with quality metrics
- **File Cache**: Manifest and chunk storage (Rust)
- **Chunk Store**: Ring buffer for DCDN (lock-free)

### 🤖 **AI Brain** (Machine Learning)
- **Threat Predictor**: CNN for network threat detection
- **Shard Optimizer**: ML-based CES optimization
- **Translation Pipeline**: ASR → NMT → TTS multilingual
- **Video Lipsync**: Audio-visual synchronization
- **Federated Learning**: P2P-FL with privacy preservation

### 📡 **Network Bridge** (Communication)
- **Cap'n Proto RPC**: Python ↔ Go IPC
- **LibP2P**: P2P networking with NAT traversal
- **Streaming Service**: Real-time video/audio/chat
- **FFI Bridge**: Go ↔ Rust interop
- **QUIC Transport**: Low-latency UDP for DCDN
- **DHT**: Distributed hash table for peer/content discovery

## Technology Stack

| Layer | Language | Key Technologies |
|-------|----------|------------------|
| **UI** | Python | Kivy, KivyMD, Tkinter |
| **CLI** | Python | Click, subprocess |
| **AI/ML** | Python | PyTorch, NumPy, Transformers |
| **Orchestration** | Go | LibP2P, Cap'n Proto, DHT |
| **Performance** | Rust | QUIC (quinn), Reed-Solomon, WASM, Tokio |
| **Encryption** | Rust | ChaCha20-Poly1305, Ed25519 |
| **Compression** | Rust | Brotli, Opus codec |
| **IPC** | All | Cap'n Proto (Python↔Go), FFI (Go↔Rust) |
| **Networking** | Go/Rust | LibP2P, QUIC, UDP, TCP |

## Related Documentation

- [README.md](./README.md) - Project overview and quick start
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) - Detailed architecture documentation
- [docs/VERSION.md](./docs/VERSION.md) - Version history and features
- [docs/SETUP_GUIDE.md](./docs/SETUP_GUIDE.md) - Setup and installation guide
- [python/README.md](./python/README.md) - Python layer documentation
- [go/README.md](./go/README.md) - Go node documentation
- [rust/README.md](./rust/README.md) - Rust implementation documentation
- [rust/src/dcdn/README.md](./rust/src/dcdn/README.md) - DCDN architecture
