"""
Main prediction orchestrator.
Coordinates data collection, model prediction, and threat score updates.
"""
import time
import logging
from typing import Dict, List, Optional
import threading

from client.go_client import GoNodeClient
from data.timeseries import TimeSeriesCollector
from data.peer_health import PeerHealthManager
from ai.cnn_model import ModelManager

logger = logging.getLogger(__name__)


class ThreatPredictor:
    """Main predictor that orchestrates the AI pipeline."""
    
    def __init__(self, go_client: GoNodeClient, 
                 window_size: int = 100,
                 poll_interval: float = 1.0,
                 health_threshold: float = 0.5):
        """
        Initialize threat predictor.
        
        Args:
            go_client: Go node client
            window_size: Time series window size
            poll_interval: Seconds between data collection cycles
            health_threshold: Minimum health score for peers
        """
        self.go_client = go_client
        self.poll_interval = poll_interval
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Components
        self.timeseries = TimeSeriesCollector(window_size=window_size)
        self.peer_health = PeerHealthManager(health_threshold=health_threshold)
        self.model = ModelManager(input_size=window_size)
    
    def start(self):
        """Start the prediction loop in a background thread."""
        # Defensive check: make sure the Go client is actually connected.
        # The CLI ensures this already, but library callers might forget.
        try:
            if hasattr(self.go_client, "is_connected") and not self.go_client.is_connected():
                raise RuntimeError(
                    "GoNodeClient is not connected. Call go_client.connect() "
                    "and check the return value before starting ThreatPredictor."
                )
        except Exception:
            # If the client does not expose is_connected or raises unexpectedly,
            # we fail fast rather than running a blind background loop.
            raise

        if self.running:
            logger.warning("Predictor already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Threat predictor started")
    
    def stop(self):
        """Stop the prediction loop."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        logger.info("Threat predictor stopped")
    
    def _run_loop(self):
        """Main prediction loop."""
        while self.running:
            try:
                self._collect_data()
                self._predict_and_update()
                time.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in prediction loop: {e}")
                time.sleep(self.poll_interval)
    
    def _collect_data(self):
        """Collect data from Go nodes."""
        try:
            # Get all nodes
            nodes = self.go_client.get_all_nodes()
            
            for node in nodes:
                node_id = node['id']
                
                # Get connection quality
                quality = self.go_client.get_connection_quality(node_id)
                if quality:
                    # Update time series
                    self.timeseries.add_measurement(node_id, quality['latencyMs'])
                    
                    # Update peer health
                    self.peer_health.update_peer_quality(
                        node_id,
                        quality['latencyMs'],
                        quality['jitterMs'],
                        quality['packetLoss']
                    )
                    
                    # Mark as connected
                    self.peer_health.mark_peer_connected(node_id)
                else:
                    # Connection failed
                    self.peer_health.mark_peer_failure(node_id)
            
            # Try to reconnect to failed peers
            self._reconnect_failed_peers()
            
        except Exception as e:
            logger.error(f"Error collecting data: {e}")
    
    def _predict_and_update(self):
        """Run predictions and update threat scores."""
        try:
            # Get all time series
            all_series = self.timeseries.get_all_time_series()
            
            if not all_series:
                return
            
            # Prepare sequences for prediction
            sequences = []
            node_ids = []
            
            for node_id, series in all_series.items():
                if len(series) >= 10:  # Minimum data points
                    sequences.append(series)
                    node_ids.append(node_id)
            
            if not sequences:
                return
            
            # Predict threat scores
            threat_scores = self.model.predict(sequences)
            
            # Update Go nodes
            for node_id, score in zip(node_ids, threat_scores):
                success = self.go_client.update_threat_score(node_id, float(score))
                if success:
                    logger.debug(f"Updated threat score for node {node_id}: {score:.3f}")
                else:
                    logger.warning(f"Failed to update threat score for node {node_id}")
        
        except Exception as e:
            logger.error(f"Error in prediction: {e}")
    
    def _reconnect_failed_peers(self):
        """Attempt to reconnect to failed peers."""
        best_peer = self.peer_health.get_best_peer_to_connect()
        if best_peer:
            peer_id, host, port = best_peer
            logger.info(f"Attempting to reconnect to peer {peer_id} at {host}:{port}")
            success, quality = self.go_client.connect_to_peer(peer_id, host, port)
            if success:
                self.peer_health.mark_peer_connected(peer_id)
                if quality:
                    self.peer_health.update_peer_quality(
                        peer_id,
                        quality['latencyMs'],
                        quality['jitterMs'],
                        quality['packetLoss']
                    )
            else:
                self.peer_health.mark_peer_failure(peer_id)
    
    def get_healthy_peers(self) -> List[int]:
        """Get list of healthy peer IDs."""
        return self.peer_health.get_healthy_peers()
    
    def get_peer_scores(self) -> Dict[int, float]:
        """Get health scores for all peers."""
        return self.peer_health.get_all_peer_scores()
    
    def add_peer(self, peer_id: int, host: str, port: int):
        """Add a peer to monitor."""
        self.peer_health.add_peer(peer_id, host, port)
        logger.info(f"Added peer {peer_id} at {host}:{port}")

