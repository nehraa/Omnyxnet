# Monitoring and Observability Setup

This document describes the monitoring and observability tools integrated into the Pangea Network project.

## Overview

The project now includes comprehensive monitoring and observability features:

- **Prometheus**: Metrics collection and time-series database
- **Grafana**: Metrics visualization and dashboards
- **LocalStack**: Local AWS cloud stack for testing
- **Datadog**: APM and distributed tracing
- **New Relic**: Application performance monitoring
- **Sentry**: Error tracking and monitoring

## Services with Metrics

All three core services expose Prometheus metrics:

1. **Go Orchestrator** (port 8080)
   - Metrics endpoint: `http://localhost:8080/metrics`
   - Health endpoint: `http://localhost:8080/health`
   - Tracks: RPC requests, active workers, gradient aggregations

2. **Python AI Client** (port 8081)
   - Metrics endpoint: `http://localhost:8081/metrics`
   - Tracks: Training batches, epochs, loss, accuracy, gradient updates

3. **Rust Compute Core** (port 9091)
   - Metrics endpoint: `http://localhost:9091/metrics`
   - Health endpoint: `http://localhost:9091/health`
   - Tracks: Request count, processing duration, active tasks, data bytes processed

## Getting Started

### Prerequisites

1. Docker and Docker Compose installed
2. Environment variables configured in `tools/.env`

### Starting the Stack

```bash
# From the infra directory
cd infra
docker compose up -d

# View logs
docker compose logs -f

# Stop the stack
docker compose down
```

### Accessing Services

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **LocalStack**: http://localhost:4566
- **Go Orchestrator Metrics**: http://localhost:8080/metrics
- **Python AI Metrics**: http://localhost:8081/metrics
- **Rust Compute Metrics**: http://localhost:9091/metrics

## Configuration

### Environment Variables

All monitoring credentials are configured in `tools/.env`:

```bash
# Datadog
DD_API_KEY=<your-key>
DD_SITE=us5.datadoghq.com

# New Relic
NEW_RELIC_LICENSE_KEY=<your-key>

# Sentry
SENTRY_DSN=<your-dsn>
SENTRY_SEND_DEFAULT_PII=true

# LocalStack
LOCALSTACK_AUTH_TOKEN=<your-token>
LOCALSTACK_ENDPOINT_URL=http://localhost:4566

# AWS Test Credentials (for LocalStack)
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=eu-west-2
```

### Prometheus Configuration

Prometheus is configured to scrape all services every 15 seconds. See `prometheus.yml` for details.

### Grafana Dashboards

A pre-configured dashboard "Pangea Network Metrics" is automatically provisioned showing:
- HTTP request rates
- Request latency (p95/p99)
- Error rates

Access it at: http://localhost:3000/d/pangea-metrics

## LocalStack Services

The following AWS services are available through LocalStack:
- **S3**: Object storage
- **SQS**: Message queuing
- **Lambda**: Serverless functions
- **DynamoDB**: NoSQL database

All services are accessible at: http://localhost:4566

Example usage:
```bash
# Configure AWS CLI to use LocalStack
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=eu-west-2

# Create an S3 bucket
aws --endpoint-url=http://localhost:4566 s3 mb s3://my-bucket

# List buckets
aws --endpoint-url=http://localhost:4566 s3 ls
```

## Observability Features

### Datadog APM

Datadog tracing is automatically enabled when `DD_API_KEY` is set. Traces are sent to the configured Datadog site.

### New Relic

New Relic APM is initialized in both Go and Python services. Application name defaults to the service name.

### Sentry

Sentry error tracking captures exceptions and sends them to the configured DSN. PII (Personally Identifiable Information) is included based on the `SENTRY_SEND_DEFAULT_PII` setting.

## Metrics Reference

### Go Orchestrator Metrics

- `http_requests_total`: Total HTTP requests (labels: method, endpoint, status)
- `http_request_duration_seconds`: HTTP request duration histogram
- `http_requests_errors_total`: Total HTTP errors
- `rpc_requests_total`: Total RPC requests
- `rpc_request_duration_seconds`: RPC request duration
- `active_workers`: Number of active workers (gauge)
- `gradient_aggregations_total`: Total gradient aggregations

### Python AI Client Metrics

- `http_requests_total`: Total HTTP requests
- `http_request_duration_seconds`: HTTP request duration
- `training_batches_total`: Total training batches processed
- `training_epochs_total`: Total training epochs completed
- `training_loss`: Current training loss (gauge)
- `training_accuracy`: Current training accuracy (gauge)
- `model_parameters_total`: Total model parameters (gauge)
- `gradient_updates_total`: Total gradient updates sent

### Rust Compute Metrics

- `pangea_rust_compute_http_requests_total`: Total HTTP requests
- `pangea_rust_compute_processing_duration_seconds`: Processing time histogram
- `pangea_rust_compute_active_tasks`: Number of active processing tasks
- `pangea_rust_compute_data_bytes_processed_total`: Total bytes processed
- `pangea_rust_compute_errors_total`: Total errors

## Troubleshooting

### Services not starting

```bash
# Check service logs
docker compose logs go-orchestrator
docker compose logs python-worker-1
docker compose logs rust-compute

# Check if ports are already in use
netstat -tulpn | grep -E '8080|8081|9090|9091|3000|4566'
```

### Prometheus not scraping

1. Check if services are exposing /metrics endpoints
2. Verify service names in `prometheus.yml` match docker-compose service names
3. Check Prometheus targets: http://localhost:9090/targets

### Grafana dashboard not showing data

1. Verify Prometheus is running: http://localhost:9090
2. Check Grafana datasource configuration: http://localhost:3000/datasources
3. Ensure services are generating metrics

## Development

### Adding New Metrics

**Go Service:**
```go
import "github.com/prometheus/client_golang/prometheus"

myMetric := prometheus.NewCounter(prometheus.CounterOpts{
    Name: "my_metric_total",
    Help: "Description of my metric",
})
prometheus.MustRegister(myMetric)
myMetric.Inc()
```

**Python Service:**
```python
from prometheus_client import Counter

my_metric = Counter('my_metric_total', 'Description of my metric')
my_metric.inc()
```

**Rust Service:**
```rust
use prometheus::{Counter, Opts};

let my_metric = Counter::with_opts(
    Opts::new("my_metric_total", "Description of my metric")
).unwrap();
my_metric.inc();
```

## Security Notes

1. **LocalStack**: Only for development/testing. Never use in production with real AWS credentials.
2. **Grafana**: Change the default admin password immediately.
3. **API Keys**: Keep `tools/.env` secure and never commit real credentials to git.
4. **Sentry PII**: Be aware that `send_default_pii=true` includes user information in error reports.

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [LocalStack Documentation](https://docs.localstack.cloud/)
- [Datadog APM](https://docs.datadoghq.com/tracing/)
- [New Relic APM](https://docs.newrelic.com/docs/apm/)
- [Sentry Documentation](https://docs.sentry.io/)
