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
    
    def _run_event_loop(self):
        """Run the Cap'n Proto event loop in a background thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()
    
    def connect(self) -> bool:
        """Connect to Go node. Returns True if successful."""
        try:
            # Create a new event loop for the background thread
            self._loop = asyncio.new_event_loop()
            
            # Start the event loop in a background thread
            self._loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
            self._loop_thread.start()
            
            # Wait a bit for the loop to start
            time.sleep(0.1)
            
            # Connect using asyncio.run_coroutine_threadsafe
            async def _async_connect():
                async with capnp.kj_loop():
                    # Load schema
                    self.schema = capnp.load(self.schema_path)
                    
                    # Connect to Go node using AsyncIoStream
                    sock = await capnp.AsyncIoStream.create_connection(self.host, self.port)
                    self.client = capnp.TwoPartyClient(sock)
                    self.service = self.client.bootstrap().cast_as(self.schema.NodeService)
                    self._connected = True
                    logger.info(f"Connected to Go node at {self.host}:{self.port}")
                    
                    # Keep the loop alive
                    while self._connected:
                        await asyncio.sleep(0.1)
            
            # Schedule the connection in the background loop
            future = asyncio.run_coroutine_threadsafe(_async_connect(), self._loop)
            
            # Wait for connection to establish
            time.sleep(0.5)
            
            return self._connected
        except Exception as e:
            logger.error(f"Failed to connect to Go node: {e}")
            self._connected = False
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

