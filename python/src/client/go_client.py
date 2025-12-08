"""
Cap'n Proto RPC client for connecting to Go nodes.
Provides easy-to-use functions for Python to interact with Go nodes.
"""
import capnp
import socket
import logging
import threading
import time
import sys
import asyncio
from typing import Optional, List, Dict, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Add parent directory for relative imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.paths import get_go_schema_path

logger = logging.getLogger(__name__)


class GoNodeClient:
    """Client for connecting to a Go node via Cap'n Proto RPC."""
    
    def __init__(self, host: str = "localhost", port: int = 8080, schema_path: str = None):
        """
        Initialize Go node client.
        
        Args:
            host: Go node host address
            port: Go node RPC port (default 8080)
            schema_path: Path to schema.capnp file (if None, uses absolute path from project root)
        """
        self.host = host
        self.port = port
        
        # Use absolute path if not provided
        if schema_path is None:
            self.schema_path = get_go_schema_path()
        else:
            # Convert to absolute path if relative
            schema_path_obj = Path(schema_path)
            if not schema_path_obj.is_absolute():
                # Try to resolve relative to current working directory
                self.schema_path = str(Path.cwd() / schema_path_obj)
            else:
                self.schema_path = schema_path
        
        self.client = None
        self.service = None
        self.schema = None
        self._connected = False
        self._loop_thread = None
        self._loop = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._connection_event = threading.Event()
        self._connection_error = None
        self._connection_future = None
    
    def _run_event_loop(self):
        """Run the Cap'n Proto event loop in a background thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()
    
    def connect(self) -> bool:
        """Connect to Go node. Returns True if successful."""
        try:
            # Reset connection state
            self._connection_event.clear()
            self._connection_error = None
            
            # Create a new event loop for the background thread
            self._loop = asyncio.new_event_loop()
            
            # Start the event loop in a background thread
            self._loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
            self._loop_thread.start()
            
            # Wait for the loop to start (with proper synchronization)
            max_retries = 10
            for _ in range(max_retries):
                if self._loop.is_running():
                    break
                time.sleep(0.01)
            
            if not self._loop.is_running():
                raise RuntimeError("Event loop failed to start")
            
            # Connect using asyncio.run_coroutine_threadsafe
            async def _async_connect():
                try:
                    async with capnp.kj_loop():
                        # Load schema
                        self.schema = capnp.load(self.schema_path)
                        
                        # Connect to Go node using AsyncIoStream
                        sock = await capnp.AsyncIoStream.create_connection(self.host, self.port)
                        self.client = capnp.TwoPartyClient(sock)
                        self.service = self.client.bootstrap().cast_as(self.schema.NodeService)
                        self._connected = True
                        logger.info(f"Connected to Go node at {self.host}:{self.port}")
                        
                        # Signal connection success
                        self._connection_event.set()
                        
                        # Keep the loop alive
                        while self._connected:
                            await asyncio.sleep(0.1)
                except Exception as e:
                    self._connection_error = e
                    self._connection_event.set()  # Signal even on error
                    raise
            
            # Schedule the connection in the background loop
            self._connection_future = asyncio.run_coroutine_threadsafe(_async_connect(), self._loop)
            
            # Wait for connection with timeout (proper synchronization instead of sleep)
            if not self._connection_event.wait(timeout=5.0):
                # Cancel the future on timeout to clean up the background task
                if self._connection_future:
                    self._connection_future.cancel()
                raise TimeoutError("Connection timed out")
            
            # Check if connection failed
            if self._connection_error:
                raise self._connection_error
            
            return self._connected
        except Exception as e:
            logger.error(f"Failed to connect to Go node: {e}")
            self._connected = False
            # Cancel any pending future to prevent coroutine from continuing
            if self._connection_future:
                self._connection_future.cancel()
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(self._loop.stop)
            return False
    
    def disconnect(self):
        """Disconnect from Go node."""
        self._connected = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=2.0)
        if self.client:
            # Cap'n Proto client cleanup
            pass
        logger.info("Disconnected from Go node")
    
    def is_connected(self) -> bool:
        """Check if connected to Go node."""
        return self._connected
    
    # Quick control functions - easy to execute
    
    def get_all_nodes(self) -> List[Dict]:
        """Get all nodes data. Returns list of node dictionaries."""
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_get_all_nodes():
            result = await self.service.getAllNodes()
            nodes = []
            for node in result.nodes.nodes:
                nodes.append({
                    'id': node.id,
                    'status': node.status,
                    'latencyMs': node.latencyMs,
                    'threatScore': node.threatScore
                })
            return nodes

        try:
            future = asyncio.run_coroutine_threadsafe(_async_get_all_nodes(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error getting all nodes: {e}")
            return []
    
    def get_node(self, node_id: int) -> Optional[Dict]:
        """Get specific node data by ID."""
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_get_node():
            query = self.schema.NodeQuery.new_message()
            query.nodeId = node_id
            result = await self.service.getNode(query)
            node = result.node
            return {
                'id': node.id,
                'status': node.status,
                'latencyMs': node.latencyMs,
                'threatScore': node.threatScore
            }
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_get_node(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error getting node {node_id}: {e}")
            return None
    
    def get_connection_quality(self, peer_id: int) -> Optional[Dict]:
        """Get connection quality metrics for a peer."""
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_get_quality():
            result = await self.service.getConnectionQuality(peer_id)
            quality = result.quality
            return {
                'latencyMs': quality.latencyMs,
                'jitterMs': quality.jitterMs,
                'packetLoss': quality.packetLoss
            }
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_get_quality(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error getting connection quality for peer {peer_id}: {e}")
            return None
    
    def update_threat_score(self, node_id: int, threat_score: float) -> bool:
        """Update threat score for a node. Returns True if successful."""
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_update():
            update = self.schema.NodeUpdate.new_message()
            update.nodeId = node_id
            update.threatScore = threat_score
            result = await self.service.updateNode(update)
            return result.success
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_update(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error updating threat score for node {node_id}: {e}")
            return False
    
    def connect_to_peer(self, peer_id: int, host: str, port: int) -> Tuple[bool, Optional[Dict]]:
        """
        Connect to a new peer. Returns (success, quality_dict).
        
        Args:
            peer_id: ID of the peer to connect to
            host: Peer host address
            port: Peer port
            
        Returns:
            Tuple of (success: bool, quality: Optional[Dict])
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_connect_peer():
            peer = self.schema.PeerAddress.new_message()
            peer.peerId = peer_id
            peer.host = host
            peer.port = port
            result = await self.service.connectToPeer(peer)
            
            if result.success:
                quality = result.quality
                return True, {
                    'latencyMs': quality.latencyMs,
                    'jitterMs': quality.jitterMs,
                    'packetLoss': quality.packetLoss
                }
            return False, None
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_connect_peer(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error connecting to peer {peer_id} at {host}:{port}: {e}")
            return False, None
    
    def disconnect_peer(self, peer_id: int) -> bool:
        """Disconnect from a peer. Returns True if successful."""
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_disconnect():
            result = await self.service.disconnectPeer(peer_id)
            return result.success
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_disconnect(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error disconnecting peer {peer_id}: {e}")
            return False
    
    def get_connected_peers(self) -> List[int]:
        """Get list of connected peer IDs."""
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_get_peers():
            result = await self.service.getConnectedPeers()
            return list(result.peers)
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_get_peers(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error getting connected peers: {e}")
            return []
    
    def send_message(self, peer_id: int, data: bytes) -> bool:
        """Send a message to a peer. Returns True if successful."""
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_send():
            msg = self.schema.Message.new_message()
            msg.toPeerId = peer_id
            msg.data = data
            result = await self.service.sendMessage(msg)
            return result.success
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_send(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error sending message to peer {peer_id}: {e}")
            return False
    
    def get_network_metrics(self) -> Optional[Dict]:
        """Get network metrics for shard optimization."""
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_get_metrics():
            result = await self.service.getNetworkMetrics()
            metrics = result.metrics
            return {
                'avgRttMs': metrics.avgRttMs,
                'packetLoss': metrics.packetLoss,
                'bandwidthMbps': metrics.bandwidthMbps,
                'peerCount': metrics.peerCount,
                'cpuUsage': metrics.cpuUsage,
                'ioCapacity': metrics.ioCapacity
            }
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_get_metrics(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error getting network metrics: {e}")
            return None
    
    # CES Pipeline operations
    
    def ces_process(self, data: bytes, compression_level: int = 3) -> Optional[List[bytes]]:
        """
        Process data through CES pipeline (Compress, Encrypt, Shard).
        
        Args:
            data: Raw data to process
            compression_level: Compression level (0-22, default 3)
            
        Returns:
            List of shard data bytes, or None on error
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_ces_process():
            request = self.schema.CesProcessRequest.new_message()
            request.data = data
            request.compressionLevel = compression_level
            result = await self.service.cesProcess(request)
            
            if not result.response.success:
                error_msg = result.response.errorMsg
                logger.error(f"CES process failed: {error_msg}")
                return None
            
            # Extract shard data
            shards = []
            for shard in result.response.shards:
                shards.append(bytes(shard.data))
            
            return shards
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_ces_process(), self._loop)
            return future.result(timeout=10.0)
        except Exception as e:
            logger.error(f"Error in CES process: {e}")
            return None
    
    def ces_reconstruct(self, shards: List[bytes], shard_present: List[bool], compression_level: int = 3) -> Optional[bytes]:
        """
        Reconstruct data from shards (reverse CES pipeline).
        
        Args:
            shards: List of shard data (can include None/empty for missing shards)
            shard_present: Boolean list indicating which shards are present
            compression_level: Compression level used (must match original)
            
        Returns:
            Reconstructed data bytes, or None on error
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        if len(shards) != len(shard_present):
            raise ValueError("shards and shard_present must have same length")
        
        async def _async_ces_reconstruct():
            request = self.schema.CesReconstructRequest.new_message()
            request.compressionLevel = compression_level
            
            # Build shards list
            shard_list = request.init('shards', len(shards))
            for i, shard_data in enumerate(shards):
                shard_msg = shard_list[i]
                shard_msg.index = i
                if shard_data:
                    shard_msg.data = shard_data
                else:
                    shard_msg.data = b''
            
            # Build present list
            present_list = request.init('shardPresent', len(shard_present))
            for i, present in enumerate(shard_present):
                present_list[i] = present
            
            result = await self.service.cesReconstruct(request)
            
            if not result.response.success:
                error_msg = result.response.errorMsg
                logger.error(f"CES reconstruct failed: {error_msg}")
                return None
            
            return bytes(result.response.data)
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_ces_reconstruct(), self._loop)
            return future.result(timeout=10.0)
        except Exception as e:
            logger.error(f"Error in CES reconstruct: {e}")
            return None
    
    def upload(self, data: bytes, target_peers: List[int]) -> Optional[Dict]:
        """
        High-level upload: CES process + distribute to peers.
        
        Args:
            data: Raw data to upload
            target_peers: List of peer IDs to distribute shards to
            
        Returns:
            File manifest dictionary with shard locations, or None on error
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        if not target_peers or len(target_peers) == 0:
            raise ValueError("target_peers cannot be empty or None")
        
        async def _async_upload():
            request = self.schema.UploadRequest.new_message()
            request.data = data
            
            # Build target peers list
            peers_list = request.init('targetPeers', len(target_peers))
            for i, peer_id in enumerate(target_peers):
                peers_list[i] = peer_id
            
            result = await self.service.upload(request)
            
            if not result.response.success:
                error_msg = result.response.errorMsg
                logger.error(f"Upload failed: {error_msg}")
                return None
            
            # Extract manifest
            manifest = result.response.manifest
            shard_locations = []
            for loc in manifest.shardLocations:
                shard_locations.append({
                    'shardIndex': loc.shardIndex,
                    'peerId': loc.peerId
                })
            
            return {
                'fileHash': manifest.fileHash,
                'fileName': manifest.fileName,
                'fileSize': manifest.fileSize,
                'shardCount': manifest.shardCount,
                'parityCount': manifest.parityCount,
                'shardLocations': shard_locations,
                'timestamp': manifest.timestamp,
                'ttl': manifest.ttl
            }
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_upload(), self._loop)
            return future.result(timeout=30.0)
        except Exception as e:
            logger.error(f"Error in upload: {e}")
            return None
    
    def download(self, shard_locations: List[Dict], file_hash: str = "") -> Optional[Tuple[bytes, int]]:
        """
        High-level download: fetch shards + CES reconstruct.
        
        Args:
            shard_locations: List of dicts with 'shardIndex' and 'peerId' keys
            file_hash: Optional file hash for cache lookup
            
        Returns:
            Tuple of (data: bytes, bytes_downloaded: int), or None on error
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_download():
            request = self.schema.DownloadRequest.new_message()
            request.fileHash = file_hash
            
            # Build shard locations list
            locs_list = request.init('shardLocations', len(shard_locations))
            for i, loc in enumerate(shard_locations):
                if 'shardIndex' not in loc or 'peerId' not in loc:
                    raise ValueError(f"shard_locations[{i}] missing required keys 'shardIndex' or 'peerId'")
                loc_msg = locs_list[i]
                loc_msg.shardIndex = loc['shardIndex']
                loc_msg.peerId = loc['peerId']
            result = await self.service.download(request)
            
            if not result.response.success:
                error_msg = result.response.errorMsg
                logger.error(f"Download failed: {error_msg}")
                return None
            
            return bytes(result.response.data), result.response.bytesDownloaded
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_download(), self._loop)
            return future.result(timeout=30.0)
        except Exception as e:
            logger.error(f"Error in download: {e}")
            return None
    
    # ========================================================================
    # Streaming Methods (Go handles all networking per Golden Rule)
    # ========================================================================
    
    def start_streaming(self, port: int, peer_host: str = "", peer_port: int = 9996, stream_type: int = 0) -> bool:
        """
        Start streaming service.
        
        Args:
            port: Local port to start streaming on
            peer_host: Remote peer host (if connecting to a peer)
            peer_port: Remote peer port
            stream_type: 0=video, 1=audio, 2=chat
            
        Returns:
            True if successful
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_start_streaming():
            config = self.schema.StreamConfig.new_message()
            config.port = port
            config.peerHost = peer_host
            config.peerPort = peer_port
            config.streamType = stream_type
            result = await self.service.startStreaming(config)
            return result.success
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_start_streaming(), self._loop)
            return future.result(timeout=10.0)
        except Exception as e:
            logger.error(f"Error starting streaming: {e}")
            return False
    
    def stop_streaming(self) -> bool:
        """Stop streaming service."""
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_stop_streaming():
            result = await self.service.stopStreaming()
            return result.success
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_stop_streaming(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error stopping streaming: {e}")
            return False
    
    def send_video_frame(self, frame_id: int, data: bytes, width: int = 640, height: int = 480, quality: int = 60) -> bool:
        """
        Send a video frame to the connected peer.
        Go handles the actual UDP networking and fragmentation.
        
        Args:
            frame_id: Unique frame identifier
            data: JPEG encoded frame data
            width: Frame width
            height: Frame height
            quality: JPEG quality (0-100)
            
        Returns:
            True if successful
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_send_frame():
            frame = self.schema.VideoFrame.new_message()
            frame.frameId = frame_id
            frame.data = data
            frame.width = width
            frame.height = height
            frame.quality = quality
            result = await self.service.sendVideoFrame(frame)
            return result.success
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_send_frame(), self._loop)
            return future.result(timeout=1.0)  # Short timeout for real-time
        except Exception as e:
            logger.error(f"Error sending video frame: {e}")
            return False
    
    def send_audio_chunk(self, data: bytes, sample_rate: int = 48000, channels: int = 1) -> bool:
        """
        Send an audio chunk to the connected peer.
        Go handles the actual UDP networking.
        
        Args:
            data: Audio samples (16-bit PCM)
            sample_rate: Sample rate in Hz
            channels: Number of audio channels
            
        Returns:
            True if successful
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_send_audio():
            chunk = self.schema.AudioChunk.new_message()
            chunk.data = data
            chunk.sampleRate = sample_rate
            chunk.channels = channels
            result = await self.service.sendAudioChunk(chunk)
            return result.success
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_send_audio(), self._loop)
            return future.result(timeout=1.0)
        except Exception as e:
            logger.error(f"Error sending audio chunk: {e}")
            return False
    
    def send_chat_message(self, peer_addr: str, message: str) -> bool:
        """
        Send a chat message to a peer.
        Go handles the actual TCP networking.
        
        Args:
            peer_addr: Peer address (host:port)
            message: Text message
            
        Returns:
            True if successful
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_send_chat():
            chat_msg = self.schema.ChatMessage.new_message()
            chat_msg.peerAddr = peer_addr
            chat_msg.message_ = message  # Note: 'message' might be reserved
            chat_msg.timestamp = int(time.time() * 1000)
            result = await self.service.sendChatMessage(chat_msg)
            return result.success
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_send_chat(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error sending chat message: {e}")
            return False
    
    def connect_stream_peer(self, host: str, port: int) -> Tuple[bool, str]:
        """
        Connect to a streaming peer.
        
        Args:
            host: Peer host
            port: Peer port
            
        Returns:
            Tuple of (success, peer_address_string)
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_connect_stream():
            result = await self.service.connectStreamPeer(host, port)
            return result.success, result.peerAddr
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_connect_stream(), self._loop)
            return future.result(timeout=10.0)
        except Exception as e:
            logger.error(f"Error connecting to stream peer: {e}")
            return False, ""
    
    def get_stream_stats(self) -> Optional[Dict]:
        """
        Get streaming statistics.
        
        Returns:
            Dict with streaming stats or None
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_get_stats():
            result = await self.service.getStreamStats()
            stats = result.stats
            return {
                'framesSent': stats.framesSent,
                'framesReceived': stats.framesReceived,
                'bytesSent': stats.bytesSent,
                'bytesReceived': stats.bytesReceived,
                'avgLatencyMs': stats.avgLatencyMs
            }
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_get_stats(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error getting stream stats: {e}")
            return None
    
    def get_chat_history(self, peer_id: Optional[str] = None) -> List[Dict]:
        """
        Get chat history from the Go communication service.
        
        This method reads the chat history from the local file stored by the
        Go communication service. The file is located at:
        ~/.pangea/communication/chat_history.json
        
        If an RPC method for getChatHistory is added to the Cap'n Proto schema
        and implemented in Go, this method can be updated to use that instead.
        
        Args:
            peer_id: Optional peer ID to filter by. If None, returns all history.
            
        Returns:
            List of chat message dictionaries with keys:
            - id: Message ID
            - from: Sender peer ID
            - to: Recipient peer ID
            - content: Message text
            - timestamp: ISO timestamp
        """
        import json
        import os
        
        # Path to chat history file stored by Go communication service
        home_dir = os.path.expanduser("~")
        history_file = os.path.join(home_dir, ".pangea", "communication", "chat_history.json")
        
        if not os.path.exists(history_file):
            logger.info(f"Chat history file not found at {history_file}")
            return []
        
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
            
            # history is a dict mapping peer_id -> list of messages
            if peer_id:
                # Return messages for specific peer
                messages = history.get(peer_id, [])
                return messages
            else:
                # Flatten all messages from all peers
                all_messages = []
                for pid, messages in history.items():
                    all_messages.extend(messages)
                # Sort by timestamp
                all_messages.sort(key=lambda m: m.get('timestamp', ''))
                return all_messages
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse chat history: {e}")
            return []
        except Exception as e:
            logger.error(f"Error reading chat history: {e}")
            return []

    # ============================================================
    # Distributed Compute Methods
    # ============================================================
    
    def submit_compute_job(self, job_id: str, input_data: bytes, 
                           split_strategy: str = "fixed",
                           min_chunk_size: int = 1024,
                           max_chunk_size: int = 65536,
                           timeout_secs: int = 300,
                           priority: int = 5) -> Tuple[bool, str]:
        """Submit a compute job to the Go orchestrator.
        
        Args:
            job_id: Unique job identifier
            input_data: The input data to process
            split_strategy: How to split data ("fixed", "adaptive", "semantic")
            min_chunk_size: Minimum chunk size in bytes
            max_chunk_size: Maximum chunk size in bytes
            timeout_secs: Job timeout in seconds
            priority: Job priority (1-10, higher = more important)
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_submit():
            manifest = self.schema.ComputeJobManifest.new_message()
            manifest.jobId = job_id
            manifest.wasmModule = b""  # WASM module for complex jobs
            manifest.inputData = input_data
            manifest.splitStrategy = split_strategy
            manifest.minChunkSize = min_chunk_size
            manifest.maxChunkSize = max_chunk_size
            manifest.verificationMode = "hash"
            manifest.timeoutSecs = timeout_secs
            manifest.retryCount = 3
            manifest.priority = priority
            manifest.redundancy = 1
            
            result = await self.service.submitComputeJob(manifest)
            return result.success, result.errorMsg
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_submit(), self._loop)
            return future.result(timeout=10.0)
        except Exception as e:
            logger.error(f"Error submitting compute job: {e}")
            return False, str(e)
    
    def get_compute_job_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a compute job.
        
        Args:
            job_id: The job identifier
            
        Returns:
            Dict with status info or None if error
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_get_status():
            result = await self.service.getComputeJobStatus(job_id)
            status = result.status
            return {
                'jobId': status.jobId,
                'status': status.status,
                'progress': status.progress,
                'completedChunks': status.completedChunks,
                'totalChunks': status.totalChunks,
                'estimatedTimeRemaining': status.estimatedTimeRemaining,
                'errorMsg': status.errorMsg
            }
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_get_status(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error getting compute job status: {e}")
            return None
    
    def get_compute_job_result(self, job_id: str, timeout_ms: int = 60000) -> Tuple[Optional[bytes], str, str]:
        """Get the result of a completed compute job.
        
        Args:
            job_id: The job identifier
            timeout_ms: How long to wait for result in milliseconds
            
        Returns:
            Tuple of (result_data, error_message, worker_node)
            worker_node is "local" or the peer ID of the remote node that executed
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_get_result():
            result = await self.service.getComputeJobResult(job_id, timeout_ms)
            if result.success:
                worker_node = result.workerNode if hasattr(result, 'workerNode') else "unknown"
                return bytes(result.result), "", worker_node
            return None, result.errorMsg, ""
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_get_result(), self._loop)
            return future.result(timeout=timeout_ms/1000 + 5)
        except Exception as e:
            logger.error(f"Error getting compute job result: {e}")
            return None, str(e), ""
    
    def cancel_compute_job(self, job_id: str) -> bool:
        """Cancel a running compute job.
        
        Args:
            job_id: The job identifier
            
        Returns:
            True if cancelled successfully
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_cancel():
            result = await self.service.cancelComputeJob(job_id)
            return result.success
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_cancel(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error cancelling compute job: {e}")
            return False
    
    def get_compute_capacity(self) -> Optional[Dict]:
        """Get compute capacity of the connected node.
        
        Returns:
            Dict with capacity info or None if error
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_get_capacity():
            result = await self.service.getCapacity()
            cap = result.capacity
            return {
                'cpuCores': cap.cpuCores,
                'ramMb': cap.ramMb,
                'currentLoad': cap.currentLoad,
                'diskMb': cap.diskMb,
                'bandwidthMbps': cap.bandwidthMbps
            }
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_get_capacity(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error getting compute capacity: {e}")
            return None
    
    # ========================================================================
    # Mandate 3: Security, Ephemeral Chat, and ML RPC Methods
    # ========================================================================
    
    def set_proxy_config(self, enabled: bool, proxy_host: str, proxy_port: int, 
                        proxy_type: str = "socks5", username: str = "", 
                        password: str = "") -> Tuple[bool, str]:
        """Configure SOCKS5/Tor proxy for communications.
        
        Args:
            enabled: Enable proxy
            proxy_host: Proxy host address
            proxy_port: Proxy port
            proxy_type: Type of proxy (socks5, socks4, http)
            username: Optional proxy username
            password: Optional proxy password
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_set_proxy():
            request = self.service.setProxyConfig_request()
            config = request.config
            config.enabled = enabled
            config.proxyType = proxy_type
            config.proxyHost = proxy_host
            config.proxyPort = proxy_port
            config.username = username
            config.passwordPresent = (password != "")
            
            result = await request.send()
            return result.success, result.errorMsg if hasattr(result, 'errorMsg') else ""
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_set_proxy(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error setting proxy config: {e}")
            return False, str(e)
    
    def get_proxy_config(self) -> Optional[Dict]:
        """Get current proxy configuration.
        
        Returns:
            Dict with proxy config or None if error
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_get_proxy():
            result = await self.service.getProxyConfig()
            config = result.config
            return {
                'enabled': config.enabled,
                'proxyType': config.proxyType,
                'proxyHost': config.proxyHost,
                'proxyPort': config.proxyPort,
                'username': config.username,
                'passwordPresent': config.passwordPresent
            }
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_get_proxy(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error getting proxy config: {e}")
            return None
    
    def set_encryption_config(self, encryption_type: str, key_exchange: str = "rsa",
                             symmetric_algo: str = "aes256", 
                             enable_signatures: bool = True) -> Tuple[bool, str]:
        """Configure encryption for communications.
        
        Args:
            encryption_type: Type of encryption (asymmetric, symmetric, none)
            key_exchange: Key exchange algorithm (rsa, ecc, dh)
            symmetric_algo: Symmetric algorithm (aes256, chacha20)
            enable_signatures: Enable digital signatures
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_set_encryption():
            request = self.service.setEncryptionConfig_request()
            config = request.config
            config.encryptionType = encryption_type
            config.keyExchangeAlgorithm = key_exchange
            config.symmetricAlgorithm = symmetric_algo
            config.enableSignatures = enable_signatures
            
            result = await request.send()
            return result.success, result.errorMsg if hasattr(result, 'errorMsg') else ""
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_set_encryption(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error setting encryption config: {e}")
            return False, str(e)
    
    def start_chat_session(self, peer_addr: str, encryption_type: str = "asymmetric") -> Tuple[bool, Optional[str], str]:
        """Start an ephemeral chat session with a peer.
        
        Args:
            peer_addr: Peer address (e.g., "worker1:8080")
            encryption_type: Type of encryption (asymmetric, symmetric, none)
            
        Returns:
            Tuple of (success, session_id, error_message)
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_start_chat():
            request = self.service.startChatSession_request()
            request.peerAddr = peer_addr
            
            enc_config = request.encryptionConfig
            enc_config.encryptionType = encryption_type
            enc_config.keyExchangeAlgorithm = "rsa"
            enc_config.symmetricAlgorithm = "aes256"
            enc_config.enableSignatures = True
            
            result = await request.send()
            session_id = result.session.sessionId if result.success else None
            error_msg = result.errorMsg if hasattr(result, 'errorMsg') else ""
            return result.success, session_id, error_msg
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_start_chat(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error starting chat session: {e}")
            return False, None, str(e)
    
    def send_ephemeral_message(self, session_id: str, from_peer: str, 
                               to_peer: str, message: bytes) -> Tuple[bool, str]:
        """Send an encrypted ephemeral message.
        
        Args:
            session_id: Chat session ID
            from_peer: Sender peer address
            to_peer: Recipient peer address
            message: Message content (will be encrypted)
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_send_message():
            request = self.service.sendEphemeralMessage_request()
            msg = request.message
            msg.fromPeer = from_peer
            msg.toPeer = to_peer
            msg.message = message
            msg.timestamp = int(time.time())
            msg.messageId = f"msg-{int(time.time())}"
            msg.encryptionType = "asymmetric"
            
            result = await request.send()
            error_msg = result.errorMsg if hasattr(result, 'errorMsg') else ""
            return result.success, error_msg
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_send_message(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error sending ephemeral message: {e}")
            return False, str(e)
    
    def receive_chat_messages(self, session_id: str) -> List[Dict]:
        """Receive messages from a chat session.
        
        Args:
            session_id: Chat session ID
            
        Returns:
            List of message dictionaries
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_receive_messages():
            request = self.service.receiveChatMessages_request()
            request.sessionId = session_id
            
            result = await request.send()
            messages = []
            for msg in result.messages:
                messages.append({
                    'from': msg.fromPeer,
                    'to': msg.toPeer,
                    'message': bytes(msg.message),
                    'timestamp': msg.timestamp,
                    'messageId': msg.messageId,
                    'encryptionType': msg.encryptionType
                })
            return messages
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_receive_messages(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error receiving chat messages: {e}")
            return []
    
    def start_ml_training(self, task_id: str, dataset_id: str, model_arch: str,
                         worker_nodes: List[str], aggregator_node: str,
                         epochs: int = 10, batch_size: int = 32) -> Tuple[bool, str]:
        """Start distributed ML training task.
        
        Args:
            task_id: Unique task identifier
            dataset_id: Dataset identifier
            model_arch: Model architecture name
            worker_nodes: List of worker node addresses
            aggregator_node: Aggregator node address
            epochs: Number of training epochs
            batch_size: Batch size
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_start_training():
            request = self.service.startMLTraining_request()
            task = request.task
            task.taskId = task_id
            task.datasetId = dataset_id
            task.modelArchitecture = model_arch
            task.aggregatorNode = aggregator_node
            task.epochs = epochs
            task.batchSize = batch_size
            
            # Set worker nodes
            workers = task.init('workerNodes', len(worker_nodes))
            for i, worker in enumerate(worker_nodes):
                workers[i] = worker
            
            result = await request.send()
            error_msg = result.errorMsg if hasattr(result, 'errorMsg') else ""
            return result.success, error_msg
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_start_training(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error starting ML training: {e}")
            return False, str(e)
    
    def get_ml_training_status(self, task_id: str) -> Optional[Dict]:
        """Get ML training task status.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Dict with training status or None if error
        """
        if not self._connected:
            raise RuntimeError("Not connected to Go node")
        
        async def _async_get_status():
            request = self.service.getMLTrainingStatus_request()
            request.taskId = task_id
            
            result = await request.send()
            status = result.status
            return {
                'taskId': status.taskId,
                'currentEpoch': status.currentEpoch,
                'totalEpochs': status.totalEpochs,
                'activeWorkers': status.activeWorkers,
                'completedWorkers': status.completedWorkers,
                'currentLoss': status.currentLoss,
                'currentAccuracy': status.currentAccuracy,
                'estimatedTimeRemaining': status.estimatedTimeRemaining
            }
        
        try:
            future = asyncio.run_coroutine_threadsafe(_async_get_status(), self._loop)
            return future.result(timeout=5.0)
        except Exception as e:
            logger.error(f"Error getting ML training status: {e}")
            return None


