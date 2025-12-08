"""Observability manager for integrating monitoring tools."""

import os
import logging
from typing import Optional

import sentry_sdk
from ddtrace import tracer
import newrelic.agent
import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)


class ObservabilityManager:
    """Manager for all observability integrations."""
    
    def __init__(self):
        self.dd_api_key = os.getenv('DD_API_KEY')
        self.dd_site = os.getenv('DD_SITE')
        self.newrelic_license_key = os.getenv('NEW_RELIC_LICENSE_KEY')
        self.newrelic_app_name = os.getenv('NEW_RELIC_APP_NAME', 'python-ai-client')
        self.sentry_dsn = os.getenv('SENTRY_DSN')
        self.sentry_send_default_pii = os.getenv('SENTRY_SEND_DEFAULT_PII', 'false').lower() == 'true'
        self.sentry_environment = os.getenv('SENTRY_ENVIRONMENT', 'production')
        self.localstack_endpoint_url = os.getenv('LOCALSTACK_ENDPOINT_URL')
        self.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_REGION', 'eu-west-2')
        
        self.aws_session = None
        self.datadog_active = False
        self.newrelic_active = False
        self.sentry_active = False
    
    def initialize(self):
        """Initialize all observability tools."""
        logger.info("🔭 Initializing observability tools...")
        
        # Initialize Datadog
        if self.dd_api_key:
            try:
                self._initialize_datadog()
                self.datadog_active = True
                logger.info("✅ Datadog tracing initialized")
            except Exception as e:
                logger.warning(f"⚠️  Failed to initialize Datadog: {e}")
        
        # Initialize New Relic
        if self.newrelic_license_key:
            try:
                self._initialize_newrelic()
                self.newrelic_active = True
                logger.info("✅ New Relic agent initialized")
            except Exception as e:
                logger.warning(f"⚠️  Failed to initialize New Relic: {e}")
        
        # Initialize Sentry
        if self.sentry_dsn:
            try:
                self._initialize_sentry()
                self.sentry_active = True
                logger.info("✅ Sentry SDK initialized")
            except Exception as e:
                logger.warning(f"⚠️  Failed to initialize Sentry: {e}")
        
        # Initialize AWS/LocalStack
        if self.localstack_endpoint_url:
            try:
                self._initialize_aws()
                logger.info("✅ AWS/LocalStack session initialized")
            except Exception as e:
                logger.warning(f"⚠️  Failed to initialize AWS/LocalStack: {e}")
    
    def _initialize_datadog(self):
        """Initialize Datadog APM tracing."""
        # Datadog tracer is automatically initialized via environment variables
        # DD_SERVICE, DD_ENV, DD_VERSION should be set in docker-compose
        tracer.configure(
            hostname=os.getenv('DD_AGENT_HOST', 'localhost'),
            port=int(os.getenv('DD_TRACE_AGENT_PORT', '8126')),
        )
    
    def _initialize_newrelic(self):
        """Initialize New Relic APM."""
        # New Relic configuration file or environment variables
        newrelic.agent.initialize()
    
    def _initialize_sentry(self):
        """Initialize Sentry error tracking."""
        sentry_sdk.init(
            dsn=self.sentry_dsn,
            environment=self.sentry_environment,
            traces_sample_rate=1.0,
            send_default_pii=self.sentry_send_default_pii,
        )
    
    def _initialize_aws(self):
        """Initialize AWS SDK to use LocalStack."""
        config = Config(
            region_name=self.aws_region,
            signature_version='s3v4',
            retries={
                'max_attempts': 3,
                'mode': 'standard'
            }
        )
        
        self.aws_session = boto3.Session(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region
        )
    
    def get_s3_client(self):
        """Get S3 client configured for LocalStack."""
        if self.aws_session:
            return self.aws_session.client(
                's3',
                endpoint_url=self.localstack_endpoint_url,
                use_ssl=False
            )
        return None
    
    def get_sqs_client(self):
        """Get SQS client configured for LocalStack."""
        if self.aws_session:
            return self.aws_session.client(
                'sqs',
                endpoint_url=self.localstack_endpoint_url,
                use_ssl=False
            )
        return None
    
    def get_dynamodb_client(self):
        """Get DynamoDB client configured for LocalStack."""
        if self.aws_session:
            return self.aws_session.client(
                'dynamodb',
                endpoint_url=self.localstack_endpoint_url,
                use_ssl=False
            )
        return None
    
    def get_lambda_client(self):
        """Get Lambda client configured for LocalStack."""
        if self.aws_session:
            return self.aws_session.client(
                'lambda',
                endpoint_url=self.localstack_endpoint_url,
                use_ssl=False
            )
        return None
    
    def capture_error(self, error: Exception):
        """Capture an error to Sentry."""
        if self.sentry_active:
            sentry_sdk.capture_exception(error)
    
    def capture_message(self, message: str):
        """Capture a message to Sentry."""
        if self.sentry_active:
            sentry_sdk.capture_message(message)
    
    def shutdown(self):
        """Gracefully shutdown observability tools."""
        logger.info("🔭 Shutting down observability tools...")
        
        if self.sentry_active:
            sentry_sdk.flush(timeout=2.0)
