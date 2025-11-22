"""
AI-powered shard parameter optimizer for CES pipeline.
Uses ML to determine optimal (k, m) shard configuration based on network conditions.
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import torch
import torch.nn as nn
from dataclasses import dataclass
from datetime import datetime


@dataclass
class NetworkMetrics:
    """Network performance metrics"""
    avg_rtt_ms: float  # Average round-trip time
    packet_loss: float  # Packet loss rate (0-1)
    bandwidth_mbps: float  # Available bandwidth
    peer_count: int  # Number of available peers
    cpu_usage: float  # Local CPU usage (0-1)
    io_capacity: float  # I/O capacity metric


@dataclass
class ShardConfig:
    """Shard configuration parameters"""
    k: int  # Number of data shards
    m: int  # Number of parity shards
    confidence: float  # Model confidence (0-1)


class ShardOptimizerNN(nn.Module):
    """Neural network for predicting optimal shard parameters"""
    
    def __init__(self, input_size: int = 6, hidden_size: int = 32):
        super(ShardOptimizerNN, self).__init__()
        
        self.network = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size, 16),
            nn.ReLU(),
            nn.Linear(16, 2)  # Output: k and m
        )
        
        # Separate head for confidence estimation
        self.confidence_head = nn.Sequential(
            nn.Linear(input_size, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass
        Returns: (shard_params, confidence)
        """
        shard_params = self.network(x)
        confidence = self.confidence_head(x)
        return shard_params, confidence


class ShardOptimizer:
    """AI-powered shard optimizer"""
    
    def __init__(self, model_path: Optional[Path] = None):
        """
        Initialize optimizer
        
        Args:
            model_path: Path to saved model (if available)
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = ShardOptimizerNN().to(self.device)
        self.model.eval()
        
        # Load model if available
        if model_path and model_path.exists():
            self.load_model(model_path)
        
        # Historical data for learning
        self.history: List[Dict] = []
        self.max_history = 1000
        
        # Default configurations based on conditions
        self.default_configs = {
            'low_quality': ShardConfig(k=6, m=6, confidence=0.8),  # 50% redundancy
            'medium_quality': ShardConfig(k=8, m=4, confidence=0.9),  # 33% redundancy
            'high_quality': ShardConfig(k=10, m=3, confidence=0.95),  # 23% redundancy
        }
    
    def normalize_metrics(self, metrics: NetworkMetrics) -> torch.Tensor:
        """Normalize input metrics for the neural network"""
        # Normalize all values to [0, 1] range
        normalized = np.array([
            min(metrics.avg_rtt_ms / 1000.0, 1.0),  # Cap at 1000ms
            metrics.packet_loss,  # Already 0-1
            min(metrics.bandwidth_mbps / 1000.0, 1.0),  # Cap at 1Gbps
            min(metrics.peer_count / 100.0, 1.0),  # Cap at 100 peers
            metrics.cpu_usage,  # Already 0-1
            metrics.io_capacity,  # Already 0-1
        ], dtype=np.float32)
        
        return torch.from_numpy(normalized).to(self.device)
    
    def predict(self, metrics: NetworkMetrics) -> ShardConfig:
        """
        Predict optimal shard configuration
        
        Args:
            metrics: Current network metrics
            
        Returns:
            ShardConfig with optimal k, m, and confidence
        """
        # Normalize inputs
        input_tensor = self.normalize_metrics(metrics).unsqueeze(0)
        
        # Make prediction
        with torch.no_grad():
            shard_params, confidence = self.model(input_tensor)
        
        # Extract values
        k = int(torch.clamp(shard_params[0, 0], min=4, max=16).item())
        m = int(torch.clamp(shard_params[0, 1], min=2, max=10).item())
        conf = confidence[0, 0].item()
        
        # Ensure m <= k (redundancy can't exceed data)
        m = min(m, k)
        
        # If confidence is low, use heuristic fallback
        if conf < 0.6:
            return self._heuristic_config(metrics)
        
        return ShardConfig(k=k, m=m, confidence=conf)
    
    def _heuristic_config(self, metrics: NetworkMetrics) -> ShardConfig:
        """
        Fallback heuristic-based configuration
        
        Strategy:
        - High packet loss or high RTT -> More redundancy (lower k/m ratio)
        - Low bandwidth -> Fewer total shards
        - Few peers -> More redundancy to ensure availability
        """
        # Calculate network quality score
        quality_score = (
            (1.0 - metrics.packet_loss) * 0.4 +  # Packet loss weight
            (1.0 - min(metrics.avg_rtt_ms / 500.0, 1.0)) * 0.3 +  # RTT weight
            (min(metrics.bandwidth_mbps / 100.0, 1.0)) * 0.3  # Bandwidth weight
        )
        
        # Select configuration based on quality
        if quality_score > 0.7:
            config = self.default_configs['high_quality']
        elif quality_score > 0.4:
            config = self.default_configs['medium_quality']
        else:
            config = self.default_configs['low_quality']
        
        # Adjust based on peer count
        if metrics.peer_count < 5:
            # Few peers, increase redundancy
            config = ShardConfig(k=max(4, config.k - 2), m=config.m + 2, confidence=0.7)
        
        return config
    
    async def optimize_with_feedback(
        self,
        metrics: NetworkMetrics,
        file_size_bytes: int
    ) -> ShardConfig:
        """
        Optimize shard config with consideration for file size
        
        Args:
            metrics: Current network metrics
            file_size_bytes: Size of file to shard
            
        Returns:
            Optimized ShardConfig
        """
        # Base prediction
        config = self.predict(metrics)
        
        # Adjust for file size
        # Small files: Fewer shards (overhead matters more)
        # Large files: More shards (parallel transfer benefits)
        if file_size_bytes < 1024 * 1024:  # < 1MB
            config.k = max(4, config.k - 2)
            config.m = max(2, config.m - 1)
        elif file_size_bytes > 100 * 1024 * 1024:  # > 100MB
            config.k = min(16, config.k + 2)
            config.m = min(10, config.m + 1)
        
        # Store for learning
        self.record_decision(metrics, config, file_size_bytes)
        
        return config
    
    def record_decision(
        self,
        metrics: NetworkMetrics,
        config: ShardConfig,
        file_size: int,
        success: Optional[bool] = None
    ):
        """Record a decision for future learning"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'rtt': metrics.avg_rtt_ms,
                'packet_loss': metrics.packet_loss,
                'bandwidth': metrics.bandwidth_mbps,
                'peer_count': metrics.peer_count,
                'cpu_usage': metrics.cpu_usage,
                'io_capacity': metrics.io_capacity,
            },
            'config': {
                'k': config.k,
                'm': config.m,
            },
            'file_size': file_size,
            'success': success,
        }
        
        self.history.append(record)
        
        # Limit history size
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def train_from_history(self, epochs: int = 100, lr: float = 0.001):
        """
        Train model from recorded history
        
        This implements online learning from operational data.
        """
        if len(self.history) < 50:
            print("Not enough history data for training")
            return
        
        self.model.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        criterion = nn.MSELoss()
        
        # Prepare training data
        X = []
        y_k = []
        y_m = []
        
        for record in self.history:
            m = record['metrics']
            X.append([
                m['rtt'] / 1000.0,
                m['packet_loss'],
                m['bandwidth'] / 1000.0,
                m['peer_count'] / 100.0,
                m['cpu_usage'],
                m['io_capacity'],
            ])
            y_k.append(record['config']['k'])
            y_m.append(record['config']['m'])
        
        X_tensor = torch.tensor(X, dtype=torch.float32).to(self.device)
        y_tensor = torch.tensor(list(zip(y_k, y_m)), dtype=torch.float32).to(self.device)
        
        # Training loop
        for epoch in range(epochs):
            optimizer.zero_grad()
            shard_params, _ = self.model(X_tensor)
            loss = criterion(shard_params, y_tensor)
            loss.backward()
            optimizer.step()
            
            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch+1}/{epochs}, Loss: {loss.item():.4f}")
        
        self.model.eval()
        print(f"Training complete. Final loss: {loss.item():.4f}")
    
    def save_model(self, path: Path):
        """Save model to disk"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'history': self.history,
        }, path)
        print(f"Model saved to {path}")
    
    def load_model(self, path: Path):
        """Load model from disk"""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.history = checkpoint.get('history', [])
        self.model.eval()
        print(f"Model loaded from {path}")
    
    def save_history(self, path: Path):
        """Save decision history to JSON"""
        with open(path, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def load_history(self, path: Path):
        """Load decision history from JSON"""
        with open(path, 'r') as f:
            self.history = json.load(f)


def _example_usage():
    """Example usage (for documentation purposes only)"""
    async def run_example():
        optimizer = ShardOptimizer()
        
        # Simulate network metrics
        metrics = NetworkMetrics(
            avg_rtt_ms=50.0,
            packet_loss=0.01,
            bandwidth_mbps=100.0,
            peer_count=10,
            cpu_usage=0.3,
            io_capacity=0.8
        )
        
        # Get optimal configuration
        config = await optimizer.optimize_with_feedback(metrics, file_size_bytes=10*1024*1024)
        
        print(f"Optimal shard config: k={config.k}, m={config.m}")
        print(f"Redundancy: {config.m/config.k*100:.1f}%")
        print(f"Confidence: {config.confidence:.2f}")
    
    return run_example


if __name__ == '__main__':
    # Only run example when module is executed directly
    asyncio.run(_example_usage()())
