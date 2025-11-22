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

