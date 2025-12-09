# Pangea Network Tools Guide

**Complete guide for all integrated tools, monitoring, and observability features**

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Monitoring & Observability](#monitoring--observability)
- [CI/Code Quality Tools](#cicode-quality-tools)
- [Local Development](#local-development)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git
- Copy `tools/.env.example` to `tools/.env` and configure your credentials

### Start All Services

```bash
# Navigate to infrastructure directory
cd infra

# Start all services (monitoring, LocalStack, and application services)
docker compose up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

### Access Dashboard

Once started, access the following services:

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| **Grafana** | http://localhost:3000 | admin / changeme |
| **Prometheus** | http://localhost:9090 | - |
| **LocalStack** | http://localhost:4566 | - |
| **Go Orchestrator Metrics** | http://localhost:8080/metrics | - |
| **Python AI Metrics** | http://localhost:8081/metrics | - |
| **Rust Compute Metrics** | http://localhost:9091/metrics | - |

---

## Monitoring & Observability

### Prometheus

**What it does:** Collects metrics from all services at 15-second intervals.

**Configuration:** Edit `prometheus.yml` to add/modify scrape targets.

**Usage:**
```bash
# Check Prometheus targets status
curl http://localhost:9090/api/v1/targets

# Query metrics
curl 'http://localhost:9090/api/v1/query?query=http_requests_total'
```

**Available Metrics:**
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency histogram
- `active_workers` - Active worker count (Go orchestrator)
- `training_loss` - Current training loss (Python AI)
- `processing_duration_seconds` - Compute processing time (Rust)

### Grafana

**What it does:** Visualizes Prometheus metrics with interactive dashboards.

**Setup:** Pre-configured with Prometheus datasource and Pangea Network dashboard.

**Usage:**
1. Navigate to http://localhost:3000
2. Login with credentials from `.env` (default: admin/changeme)
3. Open "Pangea Network Metrics" dashboard
4. Customize or create new dashboards as needed

**Changing Password:**
```bash
# Update in tools/.env
GRAFANA_ADMIN_PASSWORD=your_secure_password

# Restart Grafana
docker compose restart grafana
```

### Datadog APM

**What it does:** Distributed tracing and application performance monitoring.

**Configuration:**
```bash
# In tools/.env
DD_API_KEY=your_datadog_api_key
DD_SITE=us5.datadoghq.com  # or your region
```

**Services instrumented:**
- Go Orchestrator: Full APM with trace context propagation
- Python AI Client: Automatic instrumentation for training operations

**View traces:** Visit your Datadog APM dashboard at https://app.datadoghq.com/apm/traces

### New Relic

**What it does:** Application performance monitoring and alerting.

**Configuration:**
```bash
# In tools/.env
NEW_RELIC_LICENSE_KEY=your_license_key
NEW_RELIC_APP_NAME=pangea-network  # Optional, defaults to service name
```

**Services instrumented:**
- Go Orchestrator: Transaction tracing and error tracking
- Python AI Client: Training performance monitoring

**View data:** Visit https://one.newrelic.com

### Sentry

**What it does:** Error tracking and crash reporting.

**Configuration:**
```bash
# In tools/.env
SENTRY_DSN=your_sentry_dsn
SENTRY_SEND_DEFAULT_PII=true  # Include user info in error reports
```

**Services instrumented:**
- Go Orchestrator: Panic recovery and error capture
- Python AI Client: Exception tracking during training

**View errors:** Visit your Sentry project dashboard

---

## CI/Code Quality Tools

### Travis CI

**What it does:** Continuous integration and automated testing.

**Configuration:**
```bash
# In tools/.env
TRAVIS_TOKEN=your_travis_token
```

**Usage:** Token available as environment variable in all services for CI integration.

**Documentation:** https://docs.travis-ci.com/

### Codecov

**What it does:** Code coverage analysis and reporting.

**Configuration:**
```bash
# In tools/.env
CODECOV_TOKEN=your_codecov_token
```

**Upload coverage:**
```bash
# From your CI pipeline or locally
codecov --token=$CODECOV_TOKEN
```

**View reports:** Visit https://codecov.io/gh/your-org/WGT

### CodeScene

**What it does:** Behavioral code analysis and technical debt detection.

**Configuration:**
```bash
# In tools/.env
CODESCENE_PAT_TOKEN=your_codescene_token
```

**Usage:** Token available for CodeScene API integration to analyze code complexity, hotspots, and trends.

**Documentation:** https://codescene.io/docs

---

## Local Development

### LocalStack

**What it does:** Emulates AWS services locally for development and testing.

**Enabled Services:**
- **S3**: Object storage
- **SQS**: Message queuing
- **Lambda**: Serverless functions
- **DynamoDB**: NoSQL database

**Configuration:**
```bash
# In tools/.env
LOCALSTACK_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=eu-west-2
```

**Usage Examples:**

```bash
# Configure AWS CLI for LocalStack
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=eu-west-2

# Create S3 bucket
aws --endpoint-url=http://localhost:4566 s3 mb s3://my-test-bucket

# List buckets
aws --endpoint-url=http://localhost:4566 s3 ls

# Put object
aws --endpoint-url=http://localhost:4566 s3 cp test.txt s3://my-test-bucket/

# Create SQS queue
aws --endpoint-url=http://localhost:4566 sqs create-queue --queue-name my-queue

# Send message
aws --endpoint-url=http://localhost:4566 sqs send-message \
  --queue-url http://localhost:4566/000000000000/my-queue \
  --message-body "Hello LocalStack"
```

**Python Client Usage:**
```python
from app.observability import ObservabilityManager

obs_manager = ObservabilityManager()
obs_manager.initialize()

# Get S3 client
s3_client = obs_manager.get_s3_client()
s3_client.create_bucket(Bucket='my-bucket')

# Get SQS client
sqs_client = obs_manager.get_sqs_client()
sqs_client.create_queue(QueueName='my-queue')
```

---

## Configuration

### Environment Variables

All tools are configured via `tools/.env`. Copy `tools/.env.example` to get started:

```bash
cp tools/.env.example tools/.env
# Edit tools/.env with your credentials
```

**Never commit `tools/.env` to version control!** It's already in `.gitignore`.

### Service-Specific Configuration

#### Go Orchestrator
Environment variables are automatically loaded from docker-compose. Key variables:
- `DD_API_KEY`, `DD_SITE` - Datadog
- `NEW_RELIC_LICENSE_KEY` - New Relic
- `SENTRY_DSN` - Sentry
- `LOCALSTACK_ENDPOINT_URL` - AWS SDK

#### Python AI Client
All observability tools initialized in `app/observability/manager.py`:
```python
# Automatic initialization from environment
obs_manager = ObservabilityManager()
obs_manager.initialize()
```

#### Rust Compute
Metrics exposed on port 9091. CI/code quality tokens available as environment variables.

### Docker Compose Environment

All services inherit environment variables from `tools/.env` via the `env_file` directive:

```yaml
services:
  go-orchestrator:
    env_file:
      - ../tools/.env
    environment:
      - DD_API_KEY=${DD_API_KEY}
      # Additional service-specific vars
```

---

## Troubleshooting

### Services Not Starting

**Check Docker status:**
```bash
docker ps -a
docker compose logs <service-name>
```

**Common issues:**
- Port conflicts (8080, 8081, 9090, 9091, 3000, 4566, 9090)
- Missing `.env` file
- Invalid credentials in `.env`

### Metrics Not Appearing

**Check Prometheus targets:**
```bash
curl http://localhost:9090/api/v1/targets | jq
```

All targets should be "up". If a target is "down":
1. Verify the service is running: `docker ps`
2. Check service logs: `docker compose logs <service-name>`
3. Verify port configuration in `prometheus.yml`

### Grafana Dashboard Empty

1. Check Prometheus is running and collecting data
2. Verify datasource: http://localhost:3000/datasources
3. Test query: http://localhost:3000/explore
4. Ensure services are generating metrics

### LocalStack Not Working

**Check LocalStack logs:**
```bash
docker compose logs localstack
```

**Common issues:**
- Lambda requires Docker socket mount (security warning - dev only!)
- Services not enabled in SERVICES environment variable
- Authentication token invalid

**Test LocalStack:**
```bash
aws --endpoint-url=http://localhost:4566 s3 ls
```

### APM Tools Not Receiving Data

**Datadog:**
- Verify API key is correct
- Check DD_SITE matches your region
- View agent logs in service output

**New Relic:**
- Verify license key is valid
- Check app appears in New Relic dashboard
- Allow 1-2 minutes for data to appear

**Sentry:**
- Verify DSN is correct and project exists
- Test by triggering an error in code
- Check Sentry project dashboard

### Build Failures

**Go Orchestrator:**
```bash
cd services/go-orchestrator
go mod tidy
go build .
```

**Python AI Client:**
```bash
cd services/python-ai-client
pip install -r requirements.txt
python -m app.main
```

**Rust Compute:**
```bash
cd services/rust-compute
cargo build --release
```

---

## Security Best Practices

### For Development
✅ Use test credentials in LocalStack  
✅ Keep development tokens in `.env` (gitignored)  
✅ Change Grafana default password  
✅ Use read-only Docker socket mount for LocalStack

### For Production
⚠️ **NEVER use development credentials in production!**

**Required actions before production deployment:**
1. Rotate ALL API keys and tokens
2. Use secrets management (GitHub Secrets, HashiCorp Vault, AWS Secrets Manager)
3. Remove `.env` from version control history if committed
4. Change Grafana admin password to strong value
5. Add authentication to Prometheus
6. Review Sentry PII settings for compliance (GDPR, etc.)
7. Use proper SSL/TLS certificates
8. Implement network policies and firewall rules
9. Remove or secure Docker socket mount from LocalStack
10. Regular security audits and credential rotation

**See `docs/monitoring/SECURITY_MONITORING.md` for complete security checklist.**

---

## Additional Resources

- **Monitoring Setup:** [docs/monitoring/MONITORING_SETUP.md](docs/monitoring/MONITORING_SETUP.md)
- **Security Guide:** [docs/monitoring/SECURITY_MONITORING.md](docs/monitoring/SECURITY_MONITORING.md)
- **Project README:** [README.md](README.md)

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review service logs: `docker compose logs <service>`
3. Consult tool-specific documentation linked in this guide
4. Check project README for architecture details

**Happy monitoring! 🚀📊**
