"""
1D CNN model for predicting network degradation from latency time-series.
Supports both GPU (CUDA) and CPU training/inference.
"""

import torch
import torch.nn as nn
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class LatencyPredictorCNN(nn.Module):
    """1D CNN for predicting threat scores from latency time-series."""

    def __init__(self, input_size: int = 100, num_filters: int = 64):
        """
        Initialize CNN model.

        Args:
            input_size: Length of input time series
            num_filters: Number of filters in convolutional layers
        """
        super(LatencyPredictorCNN, self).__init__()

        self.input_size = input_size

        # 1D Convolutional layers
        self.conv1 = nn.Conv1d(1, num_filters, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(num_filters)
        self.conv2 = nn.Conv1d(num_filters, num_filters * 2, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(num_filters * 2)
        self.conv3 = nn.Conv1d(num_filters * 2, num_filters, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm1d(num_filters)

        # Calculate flattened size after convolutions
        # Assuming input_size stays the same due to padding
        flattened_size = num_filters * input_size

        # Fully connected layers
        self.fc1 = nn.Linear(flattened_size, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, 1)

        # Activation and dropout
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.2)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        """
        Forward pass.

        Args:
            x: Input tensor of shape (batch_size, 1, sequence_length)

        Returns:
            Threat score tensor of shape (batch_size, 1)
        """
        # Reshape if needed (batch_size, sequence_length) -> (batch_size, 1, sequence_length)
        if x.dim() == 2:
            x = x.unsqueeze(1)

        # Convolutional layers
        x = self.relu(self.bn1(self.conv1(x)))
        x = self.relu(self.bn2(self.conv2(x)))
        x = self.relu(self.bn3(self.conv3(x)))

        # Flatten
        x = x.view(x.size(0), -1)

        # Fully connected layers
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.sigmoid(self.fc3(x))

        return x


class ModelManager:
    """Manages CNN model with GPU/CPU fallback."""

    def __init__(self, input_size: int = 100, num_filters: int = 64):
        """
        Initialize model manager.

        Args:
            input_size: Length of input time series
            num_filters: Number of filters in CNN
        """
        self.input_size = input_size
        self.device = self._get_device()
        self.model = LatencyPredictorCNN(input_size, num_filters).to(self.device)
        self.model.eval()  # Set to evaluation mode

        logger.info(f"Model initialized on device: {self.device}")

    def _get_device(self) -> torch.device:
        """Get available device (GPU if available, else CPU)."""
        if torch.cuda.is_available():
            device = torch.device("cuda")
            logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
        else:
            device = torch.device("cpu")
            logger.info("GPU not available, using CPU")
        return device

    def predict(self, sequences: List[List[float]]) -> List[float]:
        """
        Predict threat scores for multiple sequences.

        Args:
            sequences: List of time-series sequences (each is a list of floats)

        Returns:
            List of threat scores (0.0-1.0)
        """
        if not sequences:
            return []

        # Pad sequences to input_size
        padded_sequences = []
        for seq in sequences:
            if len(seq) < self.input_size:
                # Pad with last value
                padded = [seq[0]] * (self.input_size - len(seq)) + seq
            elif len(seq) > self.input_size:
                # Take last input_size values
                padded = seq[-self.input_size :]
            else:
                padded = seq
            padded_sequences.append(padded)

        # Convert to tensor
        tensor = torch.tensor(padded_sequences, dtype=torch.float32).to(self.device)

        # Predict
        with torch.no_grad():
            predictions = self.model(tensor)

        # Convert to list of floats
        return predictions.cpu().numpy().flatten().tolist()

    def predict_single(self, sequence: List[float]) -> float:
        """Predict threat score for a single sequence."""
        results = self.predict([sequence])
        return results[0] if results else 0.0

    def train_step(
        self,
        sequences: List[List[float]],
        targets: List[float],
        optimizer: Optional[torch.optim.Optimizer] = None,
        criterion: Optional[nn.Module] = None,
    ) -> float:
        """
        Perform one training step.

        Args:
            sequences: Input sequences
            targets: Target threat scores
            optimizer: Optimizer (created if None)
            criterion: Loss function (created if None)

        Returns:
            Loss value
        """
        if optimizer is None:
            optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        if criterion is None:
            criterion = nn.MSELoss()

        self.model.train()

        # Prepare data
        padded_sequences = []
        for seq in sequences:
            if len(seq) < self.input_size:
                padded = [seq[0]] * (self.input_size - len(seq)) + seq
            elif len(seq) > self.input_size:
                padded = seq[-self.input_size :]
            else:
                padded = seq
            padded_sequences.append(padded)

        tensor = torch.tensor(padded_sequences, dtype=torch.float32).to(self.device)
        targets_tensor = (
            torch.tensor(targets, dtype=torch.float32).to(self.device).unsqueeze(1)
        )

        # Forward pass
        optimizer.zero_grad()
        predictions = self.model(tensor)
        loss = criterion(predictions, targets_tensor)

        # Backward pass
        loss.backward()
        optimizer.step()

        self.model.eval()
        return loss.item()

    def save(self, path: str):
        """Save model to file."""
        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "input_size": self.input_size,
            },
            path,
        )
        logger.info(f"Model saved to {path}")

    def load(self, path: str):
        """Load model from file."""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()
        logger.info(f"Model loaded from {path}")
