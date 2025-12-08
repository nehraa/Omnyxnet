package observability

import (
"context"
"fmt"
"log"
"os"
"time"

"github.com/aws/aws-sdk-go/aws"
"github.com/aws/aws-sdk-go/aws/credentials"
"github.com/aws/aws-sdk-go/aws/session"
ddtrace "github.com/DataDog/dd-trace-go/v2/ddtrace/tracer"
"github.com/getsentry/sentry-go"
"github.com/newrelic/go-agent/v3/newrelic"
)

// Config holds configuration for observability tools
type Config struct {
// Datadog
DatadogAPIKey string
DatadogSite   string
// New Relic
NewRelicLicenseKey string
NewRelicAppName    string
// Sentry
SentryDSN               string
SentrySendDefaultPII    bool
SentryEnvironment       string
// LocalStack/AWS
LocalStackEndpointURL string
AWSAccessKeyID        string
AWSSecretAccessKey    string
AWSRegion             string
}

// LoadConfigFromEnv loads configuration from environment variables
func LoadConfigFromEnv() *Config {
return &Config{
DatadogAPIKey:           os.Getenv("DD_API_KEY"),
DatadogSite:             os.Getenv("DD_SITE"),
NewRelicLicenseKey:      os.Getenv("NEW_RELIC_LICENSE_KEY"),
NewRelicAppName:         getEnvOrDefault("NEW_RELIC_APP_NAME", "go-orchestrator"),
SentryDSN:               os.Getenv("SENTRY_DSN"),
SentrySendDefaultPII:    getEnvOrDefault("SENTRY_SEND_DEFAULT_PII", "false") == "true",
SentryEnvironment:       getEnvOrDefault("SENTRY_ENVIRONMENT", "production"),
LocalStackEndpointURL:   os.Getenv("LOCALSTACK_ENDPOINT_URL"),
AWSAccessKeyID:          os.Getenv("AWS_ACCESS_KEY_ID"),
AWSSecretAccessKey:      os.Getenv("AWS_SECRET_ACCESS_KEY"),
AWSRegion:               getEnvOrDefault("AWS_REGION", "eu-west-2"),
}
}

func getEnvOrDefault(key, defaultValue string) string {
if value := os.Getenv(key); value != "" {
return value
}
return defaultValue
}

// Manager manages all observability integrations
type Manager struct {
config        *Config
newRelicApp   *newrelic.Application
awsSession    *session.Session
datadogActive bool
sentryActive  bool
}

// NewManager creates a new observability manager
func NewManager(config *Config) *Manager {
return &Manager{
config: config,
}
}

// Initialize sets up all observability tools
func (m *Manager) Initialize() error {
log.Println("🔭 Initializing observability tools...")

// Initialize Datadog
if m.config.DatadogAPIKey != "" {
if err := m.initializeDatadog(); err != nil {
log.Printf("⚠️  Failed to initialize Datadog: %v", err)
} else {
m.datadogActive = true
log.Println("✅ Datadog tracing initialized")
}
}

// Initialize New Relic
if m.config.NewRelicLicenseKey != "" {
if err := m.initializeNewRelic(); err != nil {
log.Printf("⚠️  Failed to initialize New Relic: %v", err)
} else {
log.Println("✅ New Relic agent initialized")
}
}

// Initialize Sentry
if m.config.SentryDSN != "" {
if err := m.initializeSentry(); err != nil {
log.Printf("⚠️  Failed to initialize Sentry: %v", err)
} else {
m.sentryActive = true
log.Println("✅ Sentry SDK initialized")
}
}

// Initialize AWS/LocalStack
if m.config.LocalStackEndpointURL != "" {
if err := m.initializeAWS(); err != nil {
log.Printf("⚠️  Failed to initialize AWS/LocalStack: %v", err)
} else {
log.Println("✅ AWS/LocalStack session initialized")
}
}

return nil
}

// initializeDatadog sets up Datadog APM tracing
func (m *Manager) initializeDatadog() error {
if m.config.DatadogAPIKey == "" {
return fmt.Errorf("datadog API key not configured")
}

ddtrace.Start(
ddtrace.WithEnv(getEnvOrDefault("DD_ENV", "production")),
ddtrace.WithService(getEnvOrDefault("DD_SERVICE", "go-orchestrator")),
ddtrace.WithServiceVersion(getEnvOrDefault("DD_VERSION", "0.6.0-alpha")),
ddtrace.WithAgentAddr(getEnvOrDefault("DD_AGENT_HOST", "localhost:8126")),
)

return nil
}

// initializeNewRelic sets up New Relic APM
func (m *Manager) initializeNewRelic() error {
if m.config.NewRelicLicenseKey == "" {
return fmt.Errorf("new relic license key not configured")
}

app, err := newrelic.NewApplication(
newrelic.ConfigAppName(m.config.NewRelicAppName),
newrelic.ConfigLicense(m.config.NewRelicLicenseKey),
newrelic.ConfigDistributedTracerEnabled(true),
)
if err != nil {
return err
}

m.newRelicApp = app
return nil
}

// initializeSentry sets up Sentry error tracking
func (m *Manager) initializeSentry() error {
if m.config.SentryDSN == "" {
return fmt.Errorf("sentry DSN not configured")
}

err := sentry.Init(sentry.ClientOptions{
Dsn:              m.config.SentryDSN,
Environment:      m.config.SentryEnvironment,
TracesSampleRate: 1.0,
SendDefaultPII:   m.config.SentrySendDefaultPII,
})
if err != nil {
return err
}

return nil
}

// initializeAWS sets up AWS SDK to use LocalStack
func (m *Manager) initializeAWS() error {
if m.config.LocalStackEndpointURL == "" {
return fmt.Errorf("localstack endpoint not configured")
}

sess, err := session.NewSession(&aws.Config{
Region:      aws.String(m.config.AWSRegion),
Endpoint:    aws.String(m.config.LocalStackEndpointURL),
Credentials: credentials.NewStaticCredentials(m.config.AWSAccessKeyID, m.config.AWSSecretAccessKey, ""),
DisableSSL:  aws.Bool(true),
S3ForcePathStyle: aws.Bool(true),
})
if err != nil {
return err
}

m.awsSession = sess
return nil
}

// GetAWSSession returns the AWS session for LocalStack
func (m *Manager) GetAWSSession() *session.Session {
return m.awsSession
}

// GetNewRelicApp returns the New Relic application instance
func (m *Manager) GetNewRelicApp() *newrelic.Application {
return m.newRelicApp
}

// CaptureError captures an error to Sentry
func (m *Manager) CaptureError(err error) {
if m.sentryActive && err != nil {
sentry.CaptureException(err)
}
}

// CaptureMessage captures a message to Sentry
func (m *Manager) CaptureMessage(message string) {
if m.sentryActive {
sentry.CaptureMessage(message)
}
}

// StartDatadogSpan starts a new Datadog span
func (m *Manager) StartDatadogSpan(ctx context.Context, operationName string) (ddtrace.Span, context.Context) {
if m.datadogActive {
return ddtrace.StartSpanFromContext(ctx, operationName)
}
return nil, ctx
}

// Shutdown gracefully shuts down all observability tools
func (m *Manager) Shutdown() {
log.Println("🔭 Shutting down observability tools...")

if m.datadogActive {
ddtrace.Stop()
}

if m.sentryActive {
sentry.Flush(2 * time.Second)
}

if m.newRelicApp != nil {
m.newRelicApp.Shutdown(5 * time.Second)
}
}
