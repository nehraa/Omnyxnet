"""
Peer health management system.
Maintains lists of healthy peers, potential IPs, and peer scores.
"""

import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PeerHealth:
    """Health information for a peer."""

    peer_id: int
    host: str
    port: int
    score: float = 0.0  # Health score (0.0-1.0)
    latency_ms: float = 0.0
    jitter_ms: float = 0.0
    packet_loss: float = 0.0
    last_seen: float = 0.0
    connection_count: int = 0
    failure_count: int = 0
    is_connected: bool = False

    def update_quality(self, latency: float, jitter: float, packet_loss: float):
        """Update connection quality metrics."""
        self.latency_ms = latency
        self.jitter_ms = jitter
        self.packet_loss = packet_loss
        self.last_seen = time.time()
        self._calculate_score()

    def _calculate_score(self):
        """Calculate health score based on metrics."""
        # Lower latency = higher score
        latency_score = max(0, 1.0 - (self.latency_ms / 1000.0))  # Normalize to 1000ms

        # Lower jitter = higher score
        jitter_score = max(0, 1.0 - (self.jitter_ms / 100.0))  # Normalize to 100ms

        # Lower packet loss = higher score
        loss_score = 1.0 - self.packet_loss

        # Weighted average
        self.score = latency_score * 0.4 + jitter_score * 0.3 + loss_score * 0.3

        # Penalize for failures
        if self.failure_count > 0:
            self.score *= 1.0 / (1.0 + self.failure_count * 0.1)

    def mark_connected(self):
        """Mark peer as connected."""
        self.is_connected = True
        self.connection_count += 1
        self.failure_count = 0  # Reset on successful connection

    def mark_disconnected(self):
        """Mark peer as disconnected."""
        self.is_connected = False

    def mark_failure(self):
        """Mark a connection failure."""
        self.failure_count += 1
        self.is_connected = False
        self.score *= 0.9  # Reduce score on failure


class PeerHealthManager:
    """Manages peer health, potential IPs, and connection management."""

    def __init__(self, health_threshold: float = 0.5):
        """
        Initialize peer health manager.

        Args:
            health_threshold: Minimum score to consider peer healthy (0.0-1.0)
        """
        self.health_threshold = health_threshold
        self.peers: Dict[int, PeerHealth] = {}  # peer_id -> PeerHealth
        self.potential_ips: List[Tuple[str, int]] = (
            []
        )  # List of (host, port) for reconnection
        self.healthy_peers: List[int] = []  # List of healthy peer IDs
        self._lock = False  # Simple lock flag

    def add_peer(self, peer_id: int, host: str, port: int) -> PeerHealth:
        """Add a new peer or update existing peer."""
        if peer_id in self.peers:
            # Update existing
            self.peers[peer_id].host = host
            self.peers[peer_id].port = port
        else:
            # Create new
            self.peers[peer_id] = PeerHealth(peer_id, host, port)

        # Add to potential IPs if not already there
        if (host, port) not in self.potential_ips:
            self.potential_ips.append((host, port))

        return self.peers[peer_id]

    def update_peer_quality(
        self, peer_id: int, latency: float, jitter: float, packet_loss: float
    ):
        """Update connection quality for a peer."""
        if peer_id not in self.peers:
            logger.warning(f"Peer {peer_id} not found, cannot update quality")
            return

        self.peers[peer_id].update_quality(latency, jitter, packet_loss)
        self._update_healthy_list()

    def mark_peer_connected(self, peer_id: int):
        """Mark a peer as successfully connected."""
        if peer_id in self.peers:
            self.peers[peer_id].mark_connected()
            self._update_healthy_list()

    def mark_peer_disconnected(self, peer_id: int):
        """Mark a peer as disconnected."""
        if peer_id in self.peers:
            self.peers[peer_id].mark_disconnected()
            self._update_healthy_list()

    def mark_peer_failure(self, peer_id: int):
        """Mark a peer connection failure."""
        if peer_id in self.peers:
            self.peers[peer_id].mark_failure()
            self._update_healthy_list()

    def _update_healthy_list(self):
        """Update the list of healthy peers based on scores."""
        self.healthy_peers = [
            peer_id
            for peer_id, peer in self.peers.items()
            if peer.score >= self.health_threshold and peer.is_connected
        ]
        # Sort by score (highest first)
        self.healthy_peers.sort(key=lambda pid: self.peers[pid].score, reverse=True)

    def get_healthy_peers(self) -> List[int]:
        """Get list of healthy peer IDs (sorted by score)."""
        return self.healthy_peers.copy()

    def get_peer_score(self, peer_id: int) -> float:
        """Get health score for a peer."""
        if peer_id in self.peers:
            return self.peers[peer_id].score
        return 0.0

    def get_all_peer_scores(self) -> Dict[int, float]:
        """Get scores for all peers."""
        return {peer_id: peer.score for peer_id, peer in self.peers.items()}

    def get_potential_ips(self) -> List[Tuple[str, int]]:
        """Get list of potential IPs for reconnection."""
        return self.potential_ips.copy()

    def add_potential_ip(self, host: str, port: int):
        """Add a potential IP for future connections."""
        if (host, port) not in self.potential_ips:
            self.potential_ips.append((host, port))
            logger.info(f"Added potential IP: {host}:{port}")

    def get_best_peer_to_connect(self) -> Optional[Tuple[int, str, int]]:
        """
        Get the best peer to connect to from potential IPs.
        Returns (peer_id, host, port) or None.
        """
        # Find peers in potential IPs that aren't connected
        for host, port in self.potential_ips:
            # Check if we have a peer with this IP
            for peer_id, peer in self.peers.items():
                if peer.host == host and peer.port == port and not peer.is_connected:
                    # Return the one with highest score
                    return (peer_id, host, port)

        return None

    def get_peer_info(self, peer_id: int) -> Optional[Dict]:
        """Get full information about a peer."""
        if peer_id not in self.peers:
            return None

        peer = self.peers[peer_id]
        return {
            "peer_id": peer.peer_id,
            "host": peer.host,
            "port": peer.port,
            "score": peer.score,
            "latency_ms": peer.latency_ms,
            "jitter_ms": peer.jitter_ms,
            "packet_loss": peer.packet_loss,
            "last_seen": peer.last_seen,
            "is_connected": peer.is_connected,
            "connection_count": peer.connection_count,
            "failure_count": peer.failure_count,
        }

    def get_all_peers_info(self) -> List[Dict]:
        """Get information about all peers."""
        infos: List[Dict] = []
        for peer_id in self.peers.keys():
            info = self.get_peer_info(peer_id)
            if info is not None:
                infos.append(info)
        return infos
