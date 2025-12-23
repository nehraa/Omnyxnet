"""Prometheus metrics for the Python AI service."""

from prometheus_client import Counter, Histogram, Gauge, start_http_server
import logging

logger = logging.getLogger(__name__)

# HTTP request counter
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
)

# HTTP request duration histogram
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

# HTTP error counter
http_requests_errors_total = Counter(
    "http_requests_errors_total",
    "Total number of HTTP errors",
    ["method", "endpoint", "status"],
)

# Training metrics
training_batches_total = Counter(
    "training_batches_total", "Total number of training batches processed"
)

training_epochs_total = Counter(
    "training_epochs_total", "Total number of training epochs completed"
)

training_loss = Gauge("training_loss", "Current training loss")

training_accuracy = Gauge("training_accuracy", "Current training accuracy")

# Model metrics
model_parameters_total = Gauge(
    "model_parameters_total", "Total number of model parameters"
)

gradient_updates_total = Counter(
    "gradient_updates_total", "Total number of gradient updates sent"
)


def setup_metrics(port=8081):
    """Start the Prometheus metrics HTTP server."""
    try:
        start_http_server(port)
        logger.info(f"📊 Metrics server started on port {port}")
    except Exception as e:
        logger.error(f"❌ Failed to start metrics server: {e}")
