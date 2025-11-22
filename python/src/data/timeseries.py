"""
Time-series data collection for latency measurements.
Maintains historical data for each node for CNN prediction.
"""
import time
import logging
from typing import Dict, List, Optional
from collections import deque
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TimeSeriesPoint:
    """A single point in a time series."""
    value: float
    timestamp: float


class TimeSeriesCollector:
    """Collects and maintains time-series data for nodes."""
    
    def __init__(self, window_size: int = 100):
        """
        Initialize time-series collector.
        
        Args:
            window_size: Maximum number of points to keep per node
        """
        self.window_size = window_size
        self.series: Dict[int, deque] = {}  # node_id -> deque of TimeSeriesPoint
    
    def add_measurement(self, node_id: int, value: float, timestamp: Optional[float] = None):
        """
        Add a measurement for a node.
        
        Args:
            node_id: Node identifier
            value: Measurement value (e.g., latency)
            timestamp: Timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = time.time()
        
        if node_id not in self.series:
            self.series[node_id] = deque(maxlen=self.window_size)
        
        point = TimeSeriesPoint(value=value, timestamp=timestamp)
        self.series[node_id].append(point)
    
    def get_time_series(self, node_id: int, length: Optional[int] = None) -> List[float]:
        """
        Get time series for a node.
        
        Args:
            node_id: Node identifier
            length: Number of points to return (default: all available)
            
        Returns:
            List of values (most recent first)
        """
        if node_id not in self.series:
            return []
        
        values = [point.value for point in self.series[node_id]]
        
        if length is not None:
            return values[-length:] if len(values) > length else values
        
        return values
    
    def get_all_time_series(self, length: Optional[int] = None) -> Dict[int, List[float]]:
        """
        Get time series for all nodes.
        
        Args:
            length: Number of points to return per node
            
        Returns:
            Dictionary mapping node_id to list of values
        """
        return {
            node_id: self.get_time_series(node_id, length)
            for node_id in self.series.keys()
        }
    
    def get_latest_value(self, node_id: int) -> Optional[float]:
        """Get the most recent value for a node."""
        if node_id not in self.series or len(self.series[node_id]) == 0:
            return None
        
        return self.series[node_id][-1].value
    
    def clear_node(self, node_id: int):
        """Clear time series for a node."""
        if node_id in self.series:
            del self.series[node_id]
    
    def clear_all(self):
        """Clear all time series."""
        self.series.clear()
    
    def get_node_count(self) -> int:
        """Get number of nodes with time series data."""
        return len(self.series)
    
    def has_sufficient_data(self, node_id: int, min_points: int = 10) -> bool:
        """Check if node has sufficient data points."""
        if node_id not in self.series:
            return False
        return len(self.series[node_id]) >= min_points

