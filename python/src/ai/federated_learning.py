"""
Phase 2: Personalized Serialization via Federated Learning
P2P Federated Learning for custom voice serialization models.

This module provides:
- Custom Serialization Models (CSM) for voice compression
- Peer-to-Peer Federated Learning (P2P-FL)
- Model weight sharing during handshake
- Privacy-preserving personalization

Key Features:
- On-device training (data never leaves device)
- P2P model aggregation (no central server)
- Lightweight models for handshake exchange
- Better compression for individual voices
"""

import torch
import torch.nn as nn
import numpy as np
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FederatedConfig:
    """Configuration for federated learning"""

    # Model configuration
    model_type: str = "voice_csm"  # Custom Serialization Model
    input_dim: int = 80  # Mel spectrogram features
    latent_dim: int = 32  # Compressed representation
    hidden_dim: int = 128

    # Training configuration
    local_epochs: int = 5  # Epochs per round
    batch_size: int = 16
    learning_rate: float = 0.001

    # Federated learning
    aggregation_method: str = "fedavg"  # FedAvg, FedProx, etc.
    min_peers_for_aggregation: int = 3
    personalization_weight: float = 0.7  # Weight for local vs global model

    # Performance
    use_gpu: bool = True
    max_model_size_kb: int = 50  # For handshake exchange


class CustomSerializationModel(nn.Module):
    """
    Custom Serialization Model (CSM) for voice compression.

    Lightweight autoencoder that learns to compress voice data
    specifically for an individual speaker, achieving better
    compression ratios than generic codecs.
    """

    def __init__(self, config: FederatedConfig):
        """
        Initialize CSM.

        Args:
            config: Federated learning configuration
        """
        super().__init__()
        self.config = config

        # Encoder: Voice features → Compressed representation
        self.encoder = nn.Sequential(
            nn.Linear(config.input_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(config.hidden_dim, config.hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(config.hidden_dim // 2, config.latent_dim),
            nn.Tanh(),  # Bounded output for better compression
        )

        # Decoder: Compressed representation → Reconstructed features
        self.decoder = nn.Sequential(
            nn.Linear(config.latent_dim, config.hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(config.hidden_dim // 2, config.hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(config.hidden_dim, config.input_dim),
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass.

        Args:
            x: Input features (batch, input_dim)

        Returns:
            Tuple of (compressed, reconstructed)
        """
        compressed = self.encoder(x)
        reconstructed = self.decoder(compressed)
        return compressed, reconstructed

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """Encode voice features to compressed representation."""
        return self.encoder(x)

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """Decode compressed representation to voice features."""
        return self.decoder(z)

    def get_compression_ratio(self) -> float:
        """
        Calculate compression ratio.

        Returns:
            Compression ratio (input_size / latent_size)
        """
        return self.config.input_dim / self.config.latent_dim


class ModelWeightManager:
    """
    Manages model weight serialization and compression for handshake exchange.

    Ensures model weights are small enough to exchange during Noise Protocol
    handshake without adding significant latency.
    """

    @staticmethod
    def serialize_weights(model: nn.Module, compress: bool = True) -> bytes:
        """
        Serialize model weights to bytes.

        Args:
            model: PyTorch model
            compress: Whether to compress weights

        Returns:
            Serialized weights as bytes
        """
        import io
        import gzip

        # Get state dict
        state_dict = model.state_dict()

        # Convert to bytes
        buffer = io.BytesIO()
        torch.save(state_dict, buffer)
        weights_bytes = buffer.getvalue()

        # Compress if requested
        if compress:
            weights_bytes = gzip.compress(weights_bytes, compresslevel=9)

        logger.debug(f"Serialized weights: {len(weights_bytes)} bytes")
        return weights_bytes

    @staticmethod
    def deserialize_weights(
        weights_bytes: bytes, model: nn.Module, compressed: bool = True
    ) -> nn.Module:
        """
        Deserialize weights and load into model.

        Args:
            weights_bytes: Serialized weights
            model: Target model
            compressed: Whether weights are compressed

        Returns:
            Model with loaded weights
        """
        import io
        import gzip

        # Decompress if needed
        if compressed:
            weights_bytes = gzip.decompress(weights_bytes)

        # Load state dict
        buffer = io.BytesIO(weights_bytes)
        state_dict = torch.load(buffer, map_location="cpu")

        # Load into model
        model.load_state_dict(state_dict)

        logger.debug("Deserialized weights into model")
        return model

    @staticmethod
    def compute_weight_diff(
        model1: nn.Module, model2: nn.Module
    ) -> Dict[str, torch.Tensor]:
        """
        Compute difference between two models.

        This can be used to send only the delta during updates,
        further reducing transmission size.

        Args:
            model1: First model
            model2: Second model

        Returns:
            Dictionary of weight differences
        """
        state1 = model1.state_dict()
        state2 = model2.state_dict()

        diff = {}
        for key in state1.keys():
            diff[key] = state2[key] - state1[key]

        return diff

    @staticmethod
    def apply_weight_diff(model: nn.Module, diff: Dict[str, torch.Tensor]) -> nn.Module:
        """
        Apply weight difference to model.

        Args:
            model: Base model
            diff: Weight differences

        Returns:
            Updated model
        """
        state = model.state_dict()

        for key in diff.keys():
            state[key] = state[key] + diff[key]

        model.load_state_dict(state)
        return model


class LocalTrainer:
    """
    Local training manager for federated learning.

    Handles on-device training of the CSM using the user's private voice data.
    Data never leaves the device.
    """

    def __init__(self, config: FederatedConfig):
        """
        Initialize local trainer.

        Args:
            config: Federated learning configuration
        """
        self.config = config
        self.device = torch.device(
            "cuda" if config.use_gpu and torch.cuda.is_available() else "cpu"
        )

        # Initialize model
        self.model = CustomSerializationModel(config).to(self.device)

        # Training components
        self.optimizer = torch.optim.Adam(
            self.model.parameters(), lr=config.learning_rate
        )
        self.criterion = nn.MSELoss()

        # Training history
        self.training_history = []

        logger.info(f"Local trainer initialized on {self.device}")

    def train_on_local_data(
        self, voice_data: List[np.ndarray], epochs: Optional[int] = None
    ) -> Dict:
        """
        Train model on local voice data.

        Args:
            voice_data: List of voice feature arrays
            epochs: Number of epochs (uses config if None)

        Returns:
            Training metrics
        """
        epochs = epochs or self.config.local_epochs

        logger.info(f"Training on {len(voice_data)} voice samples for {epochs} epochs")

        self.model.train()

        total_loss = 0.0
        num_batches = 0

        for epoch in range(epochs):
            epoch_loss = 0.0

            # Process data in batches
            for i in range(0, len(voice_data), self.config.batch_size):
                batch = voice_data[i : i + self.config.batch_size]

                # Convert to tensor
                batch_tensor = torch.tensor(np.array(batch), dtype=torch.float32).to(
                    self.device
                )

                # Forward pass
                self.optimizer.zero_grad()
                _, reconstructed = self.model(batch_tensor)

                # Compute loss (reconstruction error)
                loss = self.criterion(reconstructed, batch_tensor)

                # Backward pass
                loss.backward()
                self.optimizer.step()

                epoch_loss += loss.item()
                num_batches += 1

            avg_epoch_loss = epoch_loss / max(
                1, len(voice_data) // self.config.batch_size
            )
            logger.debug(f"Epoch {epoch+1}/{epochs}, Loss: {avg_epoch_loss:.6f}")

            total_loss += avg_epoch_loss

        avg_loss = total_loss / epochs

        metrics = {
            "epochs": epochs,
            "samples": len(voice_data),
            "avg_loss": avg_loss,
            "compression_ratio": self.model.get_compression_ratio(),
        }

        self.training_history.append(metrics)

        logger.info(f"Training complete. Avg loss: {avg_loss:.6f}")

        self.model.eval()
        return metrics

    def get_model_weights(self) -> bytes:
        """
        Get serialized model weights for sharing.

        Returns:
            Compressed model weights
        """
        return ModelWeightManager.serialize_weights(self.model, compress=True)

    def load_model_weights(self, weights: bytes):
        """
        Load model weights from bytes.

        Args:
            weights: Serialized model weights
        """
        self.model = ModelWeightManager.deserialize_weights(
            weights, self.model, compressed=True
        )
        logger.info("Model weights loaded")


class FederatedAggregator:
    """
    Aggregates model updates from multiple peers.

    Implements Federated Averaging (FedAvg) and other aggregation methods
    for P2P federated learning.
    """

    @staticmethod
    def federated_average(
        models: List[nn.Module], weights: Optional[List[float]] = None
    ) -> nn.Module:
        """
        Federated Averaging (FedAvg).

        Average model parameters across multiple models.

        Args:
            models: List of models to aggregate
            weights: Optional weights for each model (e.g., based on data size)

        Returns:
            Aggregated model
        """
        if not models:
            raise ValueError("No models to aggregate")

        # Use equal weights if not provided
        if weights is None:
            weights = [1.0 / len(models)] * len(models)

        # Normalize weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]

        # Create new model with averaged weights
        aggregated_model = type(models[0])(models[0].config)
        aggregated_state = {}

        # Get first model's state dict as template
        template_state = models[0].state_dict()

        # Average each parameter
        for key in template_state.keys():
            # Weighted sum of parameters
            weighted_sum = sum(
                w * model.state_dict()[key] for w, model in zip(weights, models)
            )
            aggregated_state[key] = weighted_sum

        # Load aggregated weights
        aggregated_model.load_state_dict(aggregated_state)

        logger.info(f"Aggregated {len(models)} models using FedAvg")

        return aggregated_model

    @staticmethod
    def personalized_federated_average(
        local_model: nn.Module, peer_models: List[nn.Module], alpha: float = 0.7
    ) -> nn.Module:
        """
        Personalized Federated Learning.

        Combines local model with aggregated peer models, giving more weight
        to the local model for personalization.

        Args:
            local_model: User's local model
            peer_models: Models from peers
            alpha: Weight for local model (0-1, higher = more personalized)

        Returns:
            Personalized model
        """
        if not peer_models:
            logger.warning("No peer models, returning local model")
            return local_model

        # Aggregate peer models
        global_model = FederatedAggregator.federated_average(peer_models)

        # Blend local and global
        personalized_model = type(local_model)(local_model.config)
        personalized_state = {}

        local_state = local_model.state_dict()
        global_state = global_model.state_dict()

        for key in local_state.keys():
            personalized_state[key] = (
                alpha * local_state[key] + (1 - alpha) * global_state[key]
            )

        personalized_model.load_state_dict(personalized_state)

        logger.info(f"Created personalized model (alpha={alpha})")

        return personalized_model


class P2PFederatedLearning:
    """
    Peer-to-Peer Federated Learning coordinator.

    Manages the complete P2P-FL workflow:
    1. Local training on private data
    2. Model sharing with trusted peers
    3. Aggregation of peer models
    4. Personalized model updates
    """

    def __init__(self, config: Optional[FederatedConfig] = None):
        """
        Initialize P2P-FL coordinator.

        Args:
            config: Federated learning configuration
        """
        self.config = config or FederatedConfig()

        # Local trainer
        self.trainer = LocalTrainer(self.config)

        # Peer models cache
        self.peer_models = {}  # peer_id -> model_weights

        # Statistics
        self.round_history = []

        logger.info("P2P Federated Learning coordinator initialized")

    def train_local_round(self, voice_data: List[np.ndarray], round_num: int) -> Dict:
        """
        Execute one round of local training.

        Args:
            voice_data: Local voice data
            round_num: Current round number

        Returns:
            Round metrics
        """
        logger.info(f"Starting local training round {round_num}")

        # Train on local data
        metrics = self.trainer.train_on_local_data(voice_data)
        metrics["round"] = round_num

        self.round_history.append(metrics)

        return metrics

    def get_model_for_handshake(self) -> bytes:
        """
        Get compressed model weights for Noise Protocol handshake exchange.

        Returns:
            Compressed model weights (optimized for minimal size)
        """
        weights = self.trainer.get_model_weights()

        size_kb = len(weights) / 1024
        logger.info(f"Model for handshake: {size_kb:.2f} KB")

        if size_kb > self.config.max_model_size_kb:
            logger.warning(
                f"Model size ({size_kb:.2f} KB) exceeds target "
                f"({self.config.max_model_size_kb} KB)"
            )

        return weights

    def receive_peer_model(self, peer_id: str, model_weights: bytes):
        """
        Receive and store peer model weights.

        Args:
            peer_id: Unique peer identifier
            model_weights: Serialized model weights
        """
        logger.info(f"Received model from peer {peer_id}")
        self.peer_models[peer_id] = model_weights

    def aggregate_with_peers(self) -> bool:
        """
        Aggregate local model with peer models.

        Creates personalized model by blending local training with
        peer knowledge.

        Returns:
            True if aggregation successful
        """
        if len(self.peer_models) < self.config.min_peers_for_aggregation:
            logger.warning(
                f"Not enough peers for aggregation "
                f"({len(self.peer_models)}/{self.config.min_peers_for_aggregation})"
            )
            return False

        logger.info(f"Aggregating with {len(self.peer_models)} peer models")

        # Load peer models
        peer_model_objects = []
        for peer_id, weights in self.peer_models.items():
            model = CustomSerializationModel(self.config)
            model = ModelWeightManager.deserialize_weights(
                weights, model, compressed=True
            )
            peer_model_objects.append(model)

        # Create personalized model
        personalized_model = FederatedAggregator.personalized_federated_average(
            self.trainer.model,
            peer_model_objects,
            alpha=self.config.personalization_weight,
        )

        # Update local model
        self.trainer.model = personalized_model

        logger.info("Aggregation complete")
        return True

    def get_statistics(self) -> Dict:
        """
        Get federated learning statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "num_rounds": len(self.round_history),
            "rounds_completed": len(self.round_history),
            "num_peers": len(self.peer_models),
            "compression_ratio": self.trainer.model.get_compression_ratio(),
            "last_loss": (
                self.round_history[-1]["avg_loss"] if self.round_history else None
            ),
            "config": {
                "personalization_weight": self.config.personalization_weight,
                "aggregation_method": self.config.aggregation_method,
            },
        }

    def get_model_size(self) -> int:
        """
        Get the size of the model in bytes.

        Returns:
            Model size in bytes
        """
        weights = self.trainer.get_model_weights()
        return len(weights)


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Example: Create P2P-FL coordinator
    config = FederatedConfig(
        use_gpu=False, local_epochs=5, personalization_weight=0.7  # Use CPU for testing
    )

    fl_coordinator = P2PFederatedLearning(config)

    logger.info("P2P Federated Learning coordinator created")
    logger.info("To use:")
    logger.info("1. fl_coordinator.train_local_round(voice_data, round_num)")
    logger.info(
        "2. fl_coordinator.get_model_for_handshake() - share during Noise handshake"
    )
    logger.info("3. fl_coordinator.receive_peer_model(peer_id, weights)")
    logger.info("4. fl_coordinator.aggregate_with_peers()")
