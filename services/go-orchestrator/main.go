package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/pangea-net/go-orchestrator/pkg/gradient"
	"github.com/pangea-net/go-orchestrator/pkg/metrics"
	"github.com/pangea-net/go-orchestrator/pkg/observability"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

// OrchestratorConfig holds configuration for the orchestrator
type OrchestratorConfig struct {
	ID               uint32
	RpcAddr          string
	ListenPort       string
	MaxWorkers       int
	GracefulShutdown time.Duration
}

// Orchestrator represents the RPC server and coordination logic
type Orchestrator struct {
	config          *OrchestratorConfig
	listener        net.Listener
	ctx             context.Context
	cancel          context.CancelFunc
	gradientManager *gradient.Manager
	obsManager      *observability.Manager
}

// NewOrchestrator creates a new orchestrator instance
func NewOrchestrator(cfg *OrchestratorConfig) *Orchestrator {
	ctx, cancel := context.WithCancel(context.Background())

	// Initialize observability
	obsConfig := observability.LoadConfigFromEnv()
	obsManager := observability.NewManager(obsConfig)

	return &Orchestrator{
		config:          cfg,
		ctx:             ctx,
		cancel:          cancel,
		gradientManager: gradient.NewManager(),
		obsManager:      obsManager,
	}
}

// Start initiates the RPC server and listens for connections
func (o *Orchestrator) Start() error {
	// Initialize observability tools
	if err := o.obsManager.Initialize(); err != nil {
		log.Printf("⚠️  Failed to initialize observability: %v", err)
	}

	var err error
	o.listener, err = net.Listen("tcp", o.config.RpcAddr)
	if err != nil {
		return fmt.Errorf("failed to listen on %s: %w", o.config.RpcAddr, err)
	}

	log.Printf("🚀 Go Orchestrator started (ID: %d)", o.config.ID)
	log.Printf("📡 RPC server listening on %s", o.config.RpcAddr)
	log.Printf("🤝 Max workers: %d", o.config.MaxWorkers)
	log.Printf("⏱️  Graceful shutdown timeout: %v", o.config.GracefulShutdown)

	// Start Prometheus metrics server
	go o.startMetricsServer()

	// Simulate accepting connections (actual implementation would handle gRPC/Cap'n Proto)
	go o.acceptConnections()

	return nil
}

// startMetricsServer starts the Prometheus metrics HTTP server
func (o *Orchestrator) startMetricsServer() {
	http.Handle("/metrics", promhttp.Handler())

	// Health check endpoint
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		metrics.HTTPRequestsTotal.WithLabelValues(r.Method, "/health", "200").Inc()
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	metricsAddr := ":8080"
	log.Printf("📊 Metrics server listening on %s/metrics", metricsAddr)

	if err := http.ListenAndServe(metricsAddr, nil); err != nil {
		log.Printf("❌ Metrics server error: %v", err)
	}
}

// acceptConnections accepts incoming client connections
func (o *Orchestrator) acceptConnections() {
	for {
		select {
		case <-o.ctx.Done():
			log.Println("📤 Stopping connection acceptance")
			return
		default:
			conn, err := o.listener.Accept()
			if err != nil {
				log.Printf("⚠️  Failed to accept connection: %v", err)
				continue
			}

			// Handle connection in goroutine
			log.Printf("✅ New connection accepted from %s", conn.RemoteAddr())
			go o.handleConnection(conn)

			// Update metrics
			metrics.ActiveWorkers.Inc()
		}
	}
}

// handleConnection processes a single client connection
func (o *Orchestrator) handleConnection(conn net.Conn) {
	defer conn.Close()
	defer metrics.ActiveWorkers.Dec()

	log.Printf("🔌 Handling connection from %s", conn.RemoteAddr())

	// Track RPC requests
	start := time.Now()
	metrics.RPCRequestsTotal.WithLabelValues("connection", "success").Inc()

	// Actual message handling would occur here

	duration := time.Since(start).Seconds()
	metrics.RPCRequestDuration.WithLabelValues("connection").Observe(duration)
}

// Stop gracefully shuts down the orchestrator
func (o *Orchestrator) Stop() error {
	log.Println("🛑 Shutting down orchestrator...")

	o.cancel()

	if o.listener != nil {
		if err := o.listener.Close(); err != nil {
			log.Printf("⚠️  Error closing listener: %v", err)
		}
	}

	// Give in-flight requests time to complete
	<-time.After(o.config.GracefulShutdown)

	// Shutdown observability tools
	o.obsManager.Shutdown()

	log.Println("✅ Orchestrator shutdown complete")
	return nil
}

// main entry point
func main() {
	var (
		id               = flag.Uint("id", 1, "Orchestrator node ID")
		rpcAddr          = flag.String("rpc-addr", ":8080", "RPC server address")
		listenPort       = flag.String("listen", "0.0.0.0:8080", "Server listen address")
		maxWorkers       = flag.Int("max-workers", 10, "Maximum number of connected workers")
		gracefulShutdown = flag.Duration("shutdown-timeout", 30*time.Second, "Graceful shutdown timeout")
	)
	flag.Parse()

	config := &OrchestratorConfig{
		ID:               uint32(*id),
		RpcAddr:          *rpcAddr,
		ListenPort:       *listenPort,
		MaxWorkers:       *maxWorkers,
		GracefulShutdown: *gracefulShutdown,
	}

	orchestrator := NewOrchestrator(config)

	if err := orchestrator.Start(); err != nil {
		log.Fatalf("❌ Failed to start orchestrator: %v", err)
	}

	// Setup signal handling for graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	if err := orchestrator.Stop(); err != nil {
		log.Fatalf("❌ Error during shutdown: %v", err)
	}
}
