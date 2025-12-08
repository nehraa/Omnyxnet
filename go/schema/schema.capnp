@0x8513e0c6129c1f4c;

using Go = import "/go.capnp";
$Go.package("main");
$Go.import("main");

# Cap'n Proto schema for Pangea Net

struct Node {
    id @0 :UInt32;
    status @1 :UInt32;  # Active, Purgatory, Dead
    latencyMs @2 :Float32;
    threatScore @3 :Float32;
}

struct NodeList {
    nodes @0 :List(Node);
}

struct NodeUpdate {
    nodeId @0 :UInt32;
    latencyMs @1 :Float32;
    threatScore @2 :Float32;
}

struct NodeQuery {
    nodeId @0 :UInt32;
}

struct PeerAddress {
    peerId @0 :UInt32;
    host @1 :Text;
    port @2 :UInt16;
}

struct Message {
    toPeerId @0 :UInt32;
    data @1 :Data;
}

struct ConnectionQuality {
    latencyMs @0 :Float32;
    jitterMs @1 :Float32;
    packetLoss @2 :Float32;
}

struct NetworkMetrics {
    avgRttMs @0 :Float32;
    packetLoss @1 :Float32;
    bandwidthMbps @2 :Float32;
    peerCount @3 :UInt32;
    cpuUsage @4 :Float32;
    ioCapacity @5 :Float32;
}

# CES (Compression, Encryption, Sharding) structures
struct Shard {
    index @0 :UInt32;
    data @1 :Data;
}

struct ShardLocation {
    shardIndex @0 :UInt32;
    peerId @1 :UInt32;
}

struct FileManifest {
    fileHash @0 :Text;
    fileName @1 :Text;
    fileSize @2 :UInt64;
    shardCount @3 :UInt32;
    parityCount @4 :UInt32;
    shardLocations @5 :List(ShardLocation);
    timestamp @6 :Int64;
    ttl @7 :UInt32;
}

struct CesProcessRequest {
    data @0 :Data;
    compressionLevel @1 :Int32;
}

struct CesProcessResponse {
    success @0 :Bool;
    errorMsg @1 :Text;
    shards @2 :List(Shard);
}

struct CesReconstructRequest {
    shards @0 :List(Shard);
    shardPresent @1 :List(Bool);
    compressionLevel @2 :Int32;
}

struct CesReconstructResponse {
    success @0 :Bool;
    errorMsg @1 :Text;
    data @2 :Data;
}

struct UploadRequest {
    data @0 :Data;
    targetPeers @1 :List(UInt32);
}

struct UploadResponse {
    success @0 :Bool;
    errorMsg @1 :Text;
    manifest @2 :FileManifest;
}

struct DownloadRequest {
    shardLocations @0 :List(ShardLocation);
    fileHash @1 :Text;
}

struct DownloadResponse {
    success @0 :Bool;
    errorMsg @1 :Text;
    data @2 :Data;
    bytesDownloaded @3 :UInt64;
}

# Streaming structures for real-time video/audio/chat
# Go handles the actual networking; Python manages high-level operations
struct StreamConfig {
    port @0 :UInt16;
    peerHost @1 :Text;
    peerPort @2 :UInt16;
    streamType @3 :UInt8;  # 0=video, 1=audio, 2=chat
}

struct StreamStats {
    framesSent @0 :UInt64;
    framesReceived @1 :UInt64;
    bytesSent @2 :UInt64;
    bytesReceived @3 :UInt64;
    avgLatencyMs @4 :Float32;
}

struct VideoFrame {
    frameId @0 :UInt32;
    data @1 :Data;
    width @2 :UInt16;
    height @3 :UInt16;
    quality @4 :UInt8;
}

struct AudioChunk {
    data @0 :Data;
    sampleRate @1 :UInt32;
    channels @2 :UInt8;
}

struct ChatMessage {
    peerAddr @0 :Text;
    message @1 :Text;
    timestamp @2 :Int64;
}

interface NodeService {
    # Get a specific node by ID
    getNode @0 (query :NodeQuery) -> (node :Node);
    
    # Get all nodes
    getAllNodes @1 () -> (nodes :NodeList);
    
    # Update node state (called by Python AI)
    updateNode @2 (update :NodeUpdate) -> (success :Bool);
    
    # Update latency (called by network layer)
    updateLatency @3 (nodeId :UInt32, latencyMs :Float32) -> (success :Bool);
    
    # Stream node updates (for real-time monitoring)
    streamUpdates @4 () -> (update :NodeUpdate);
    
    # Connect to a new peer (Python can call this directly)
    connectToPeer @5 (peer :PeerAddress) -> (success :Bool, quality :ConnectionQuality);
    
    # Send a message to a peer
    sendMessage @6 (msg :Message) -> (success :Bool);
    
    # Get connection quality for a peer
    getConnectionQuality @7 (peerId :UInt32) -> (quality :ConnectionQuality);
    
    # Disconnect from a peer
    disconnectPeer @8 (peerId :UInt32) -> (success :Bool);
    
    # Get list of connected peers
    getConnectedPeers @9 () -> (peers :List(UInt32));
    
    # Get network metrics for shard optimization
    getNetworkMetrics @10 () -> (metrics :NetworkMetrics);
    
    # CES Pipeline operations
    # Process data through CES (Compress, Encrypt, Shard)
    cesProcess @11 (request :CesProcessRequest) -> (response :CesProcessResponse);
    
    # Reconstruct data from shards (reverse CES)
    cesReconstruct @12 (request :CesReconstructRequest) -> (response :CesReconstructResponse);
    
    # High-level upload: CES process + distribute to peers
    upload @13 (request :UploadRequest) -> (response :UploadResponse);
    
    # High-level download: fetch shards + CES reconstruct
    download @14 (request :DownloadRequest) -> (response :DownloadResponse);
    
    # === Streaming Services (Go handles all networking) ===
    
    # Start UDP streaming service for video/audio
    startStreaming @15 (config :StreamConfig) -> (success :Bool, errorMsg :Text);
    
    # Stop streaming service
    stopStreaming @16 () -> (success :Bool);
    
    # Send a video frame to a peer (Go handles UDP)
    sendVideoFrame @17 (frame :VideoFrame) -> (success :Bool);
    
    # Send an audio chunk to a peer (Go handles UDP)
    sendAudioChunk @18 (chunk :AudioChunk) -> (success :Bool);
    
    # Send a chat message to a peer (Go handles TCP)
    sendChatMessage @19 (message :ChatMessage) -> (success :Bool);
    
    # Connect to a streaming peer
    connectStreamPeer @20 (host :Text, port :UInt16) -> (success :Bool, peerAddr :Text);
    
    # Get streaming statistics
    getStreamStats @21 () -> (stats :StreamStats);
    
    # === Distributed Compute Service ===
    
    # Submit a new compute job
    submitComputeJob @22 (manifest :ComputeJobManifest) -> (jobId :Text, success :Bool, errorMsg :Text);
    
    # Get job status
    getComputeJobStatus @23 (jobId :Text) -> (status :ComputeJobStatus);
    
    # Get job result (blocks until complete or timeout)
    getComputeJobResult @24 (jobId :Text, timeoutMs :UInt32) -> (result :Data, success :Bool, errorMsg :Text, workerNode :Text);
    
    # Cancel a running job
    cancelComputeJob @25 (jobId :Text) -> (success :Bool);
    
    # Get node compute capacity
    getComputeCapacity @26 () -> (capacity :ComputeCapacity);
    
    # === mDNS Discovery Service ===
    
    # Get list of peers discovered via mDNS
    getMdnsDiscovered @27 () -> (peers :List(DiscoveredPeer));
    
    # Connect to an mDNS-discovered peer
    connectMdnsPeer @28 (peerID :Text) -> (success :Bool, errorMsg :Text);
    
    # === Configuration Management ===
    
    # Load configuration from disk
    loadConfig @29 () -> (config :ConfigData, success :Bool, errorMsg :Text);
    
    # Save configuration to disk
    saveConfig @30 (config :ConfigData) -> (success :Bool, errorMsg :Text);
    
    # Update a configuration value
    updateConfigValue @31 (key :Text, value :Text) -> (success :Bool);
    
    # === Security & Encryption Services (Mandate 3) ===
    
    # Configure SOCKS5/Tor proxy
    setProxyConfig @32 (config :ProxyConfig) -> (success :Bool, errorMsg :Text);
    
    # Get current proxy configuration
    getProxyConfig @33 () -> (config :ProxyConfig);
    
    # Set encryption configuration for communications
    setEncryptionConfig @34 (config :EncryptionConfig) -> (success :Bool, errorMsg :Text);
    
    # Get current encryption configuration
    getEncryptionConfig @35 () -> (config :EncryptionConfig);
    
    # Initiate key exchange with peer
    initiateKeyExchange @36 (peerAddr :Text, request :KeyExchangeRequest) -> (response :KeyExchangeResponse, success :Bool, errorMsg :Text);
    
    # Accept key exchange from peer
    acceptKeyExchange @37 (request :KeyExchangeRequest) -> (response :KeyExchangeResponse, success :Bool, errorMsg :Text);
    
    # === Ephemeral Chat Services (Mandate 3) ===
    
    # Start an ephemeral chat session with a peer
    startChatSession @38 (peerAddr :Text, encryptionConfig :EncryptionConfig) -> (session :ChatSession, success :Bool, errorMsg :Text);
    
    # Send ephemeral chat message
    sendEphemeralMessage @39 (message :EphemeralChatMessage) -> (success :Bool, errorMsg :Text);
    
    # Receive ephemeral chat messages for specific session (with authorization)
    receiveChatMessages @40 (sessionId :Text) -> (messages :List(EphemeralChatMessage));
    
    # Close chat session
    closeChatSession @41 (sessionId :Text) -> (success :Bool);
    
    # === Distributed ML Services (Mandate 3) ===
    
    # Distribute dataset to worker nodes
    distributeDataset @42 (dataset :MLDataset, workerNodes :List(Text)) -> (success :Bool, errorMsg :Text);
    
    # Submit gradient update from worker
    submitGradient @43 (update :GradientUpdate) -> (success :Bool, errorMsg :Text);
    
    # Get model update from aggregator (for workers)
    getModelUpdate @44 (modelVersion :UInt32) -> (update :ModelUpdate, success :Bool, errorMsg :Text);
    
    # Start ML training task (aggregator role)
    startMLTraining @45 (task :MLTrainingTask) -> (success :Bool, errorMsg :Text);
    
    # Get ML training status
    getMLTrainingStatus @46 (taskId :Text) -> (status :MLTrainingStatus);
    
    # Stop ML training
    stopMLTraining @47 (taskId :Text) -> (success :Bool);
}

# === Distributed Compute Structures ===

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
    priority @9 :UInt32;
    redundancy @10 :UInt32;
}

struct ComputeJobStatus {
    jobId @0 :Text;
    status @1 :Text;
    progress @2 :Float32;
    completedChunks @3 :UInt32;
    totalChunks @4 :UInt32;
    estimatedTimeRemaining @5 :UInt32;
    errorMsg @6 :Text;
}

struct ComputeCapacity {
    cpuCores @0 :UInt32;
    ramMb @1 :UInt64;
    currentLoad @2 :Float32;
    diskMb @3 :UInt64;
    bandwidthMbps @4 :Float32;
}

# === mDNS Discovery Structures ===

struct DiscoveredPeer {
    peerId @0 :Text;
    multiaddrs @1 :List(Text);
    discoveredAt @2 :Int64;
}

# === Configuration Structures ===

struct ConfigData {
    nodeId @0 :UInt32;
    capnpAddr @1 :Text;
    libp2pPort @2 :Int32;
    useLibp2p @3 :Bool;
    localMode @4 :Bool;
    bootstrapPeers @5 :List(Text);
    lastSavedAt @6 :Text;
    customSettings @7 :List(KeyValue);
}

struct KeyValue {
    key @0 :Text;
    value @1 :Text;
}

# === Security & Encryption Structures (Mandate 3) ===

# SOCKS5 Proxy Configuration for Tor support
struct ProxyConfig {
    enabled @0 :Bool;
    proxyType @1 :Text;  # "socks5", "socks4", "http"
    proxyHost @2 :Text;
    proxyPort @3 :UInt16;
    username @4 :Text;    # Optional authentication (do not expose if sensitive)
    passwordPresent @5 :Bool;  # True if password is set, actual value not exposed via getProxyConfig
}

# Encryption configuration
struct EncryptionConfig {
    encryptionType @0 :Text;  # "asymmetric", "symmetric", "none"
    keyExchangeAlgorithm @1 :Text;  # "rsa", "ecc", "dh"
    symmetricAlgorithm @2 :Text;    # "aes256", "chacha20"
    enableSignatures @3 :Bool;
}

# Ephemeral chat message structure
struct EphemeralChatMessage {
    fromPeer @0 :Text;
    toPeer @1 :Text;
    message @2 :Data;  # Encrypted message payload
    timestamp @3 :Int64;
    messageId @4 :Text;
    encryptionType @5 :Text;
    signature @6 :Data;  # Digital signature of the message
}

# Chat session management
struct ChatSession {
    sessionId @0 :Text;
    peerAddr @1 :Text;
    encryptionConfig @2 :EncryptionConfig;
    publicKey @3 :Data;  # Peer's public key
    sessionKey @4 :Data;  # Symmetric session key (if applicable)
    established @5 :Int64;  # Timestamp when session was established
}

# Key exchange request/response
struct KeyExchangeRequest {
    publicKey @0 :Data;
    algorithm @1 :Text;  # "rsa2048", "ecc256", etc.
    supportedCiphers @2 :List(Text);
    nonce @3 :Data;
}

struct KeyExchangeResponse {
    publicKey @0 :Data;
    selectedCipher @1 :Text;
    encryptedSessionKey @2 :Data;  # For symmetric mode
    nonce @3 :Data;
    signature @4 :Data;
}

# === Distributed ML Structures (Mandate 3) ===

# ML Dataset distribution
struct MLDataset {
    datasetId @0 :Text;
    dataType @1 :Text;  # "image", "text", "numeric"
    totalSamples @2 :UInt64;
    chunkSize @3 :UInt32;
    chunks @4 :List(DataChunk);
}

struct DataChunk {
    chunkId @0 :UInt32;
    data @1 :Data;
    labels @2 :Data;  # Optional labels
    checksum @3 :Text;
}

# Gradient exchange for federated learning
struct GradientUpdate {
    workerId @0 :Text;
    modelVersion @1 :UInt32;
    gradients @2 :Data;  # Serialized gradient tensors
    numSamples @3 :UInt32;
    loss @4 :Float64;
    accuracy @5 :Float64;
    timestamp @6 :Int64;
}

struct ModelUpdate {
    modelVersion @0 :UInt32;
    parameters @1 :Data;  # Serialized model parameters
    aggregationMethod @2 :Text;  # "fedavg", "fedprox", etc.
    numWorkers @3 :UInt32;
    globalLoss @4 :Float64;
    globalAccuracy @5 :Float64;
}

# Training task specification
struct MLTrainingTask {
    taskId @0 :Text;
    datasetId @1 :Text;
    modelArchitecture @2 :Text;
    hyperparameters @3 :List(KeyValue);
    workerNodes @4 :List(Text);
    aggregatorNode @5 :Text;
    epochs @6 :UInt32;
    batchSize @7 :UInt32;
}

struct MLTrainingStatus {
    taskId @0 :Text;
    currentEpoch @1 :UInt32;
    totalEpochs @2 :UInt32;
    activeWorkers @3 :UInt32;
    completedWorkers @4 :UInt32;
    currentLoss @5 :Float64;
    currentAccuracy @6 :Float64;
    estimatedTimeRemaining @7 :UInt32;
}

