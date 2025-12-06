#!/bin/bash

################################################################################
# Pangea Distributed Network - End-to-End Testing and Setup Script
#
# This script automates the complete E2E testing pipeline:
# 1. Environment setup and validation
# 2. Docker image building
# 3. Service deployment (docker-compose up)
# 4. E2E test execution
# 5. Live log streaming
# 6. Graceful teardown
################################################################################

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
INFRA_DIR="$SCRIPT_DIR/infra"
SERVICES_DIR="$PROJECT_ROOT/services"
TEST_LOG_FILE="$PROJECT_ROOT/test_e2e.log"
DOCKER_COMPOSE_FILE="$INFRA_DIR/docker-compose.yaml"
DEMO_DIR="$PROJECT_ROOT/demo"
DEMO_PORT=8000

# Test parameters
TEST_TIMEOUT=300  # 5 minutes
STARTUP_WAIT=10   # Wait for services to initialize
LOG_STREAM_DURATION=60  # Stream logs for 60 seconds

################################################################################
# Utility Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

################################################################################
# Validation
################################################################################

validate_environment() {
    print_section "STEP 1: Environment Validation"
    
    log_info "Checking for required tools..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    log_success "Docker found: $(docker --version)"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    log_success "Docker Compose found: $(docker-compose --version)"
    
    # Check docker daemon is running
    if ! docker ps &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    log_success "Docker daemon is running"
    
    # Verify project structure
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        log_error "docker-compose.yaml not found at $DOCKER_COMPOSE_FILE"
        exit 1
    fi
    log_success "Project structure validated"
    
    log_info "Disk space check..."
    DISK_AVAILABLE=$(df "$PROJECT_ROOT" | tail -1 | awk '{print $4}')
    if [ "$DISK_AVAILABLE" -lt 2097152 ]; then  # 2GB
        log_warning "Low disk space: ${DISK_AVAILABLE}KB available"
    else
        log_success "Disk space: $((DISK_AVAILABLE / 1024 / 1024))GB available"
    fi
}

################################################################################
# Test Data Setup
################################################################################

setup_test_data() {
    print_section "STEP 2: Test Data Setup"
    
    log_info "Creating test data directory..."
    mkdir -p "$PROJECT_ROOT/test_media"
    
    log_info "Generating dummy test CSV..."
    TEST_DATA_FILE="$PROJECT_ROOT/test_media/test_data.csv"
    
    # Create CSV with sample data
    {
        echo "id,feature_1,feature_2,feature_3,feature_4,feature_5,label"
        for i in {1..100}; do
            echo "$i,$(shuf -i 1-100 -n 1),$(shuf -i 1-100 -n 1),$(shuf -i 1-100 -n 1),$(shuf -i 1-100 -n 1),$(shuf -i 1-100 -n 1),$(shuf -i 0-1 -n 1)"
        done
    } > "$TEST_DATA_FILE"
    
    log_success "Test data created: $TEST_DATA_FILE ($(wc -l < "$TEST_DATA_FILE") lines)"
}

################################################################################
# Docker Build & Deploy
################################################################################

build_docker_images() {
    print_section "STEP 3: Build Docker Images"
    
    log_info "Building all service images..."
    log_info "This may take several minutes..."
    
    cd "$PROJECT_ROOT"
    
    if docker-compose -f "$DOCKER_COMPOSE_FILE" build; then
        log_success "All Docker images built successfully"
    else
        log_error "Failed to build Docker images"
        exit 1
    fi
}

start_services() {
    print_section "STEP 4: Start Services (docker-compose up)"
    
    log_info "Starting containerized environment..."
    cd "$PROJECT_ROOT"
    
    if docker-compose -f "$DOCKER_COMPOSE_FILE" up -d; then
        log_success "Services started in background"
    else
        log_error "Failed to start services"
        exit 1
    fi
    
    log_info "Waiting $STARTUP_WAIT seconds for services to initialize..."
    sleep "$STARTUP_WAIT"
    
    # Check service status
    log_info "Service status:"
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps
    
    # Verify all services are healthy
    log_info "Waiting for health checks..."
    for service in go-orchestrator rust-compute python-worker-1; do
        max_attempts=30
        attempt=0
        while [ $attempt -lt $max_attempts ]; do
            if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$service.*healthy"; then
                log_success "$service is healthy"
                break
            fi
            attempt=$((attempt + 1))
            sleep 2
        done
        if [ $attempt -eq $max_attempts ]; then
            log_warning "$service did not become healthy within timeout"
        fi
    done
}

################################################################################
# Test Execution
################################################################################

run_e2e_test() {
    print_section "STEP 5: Execute E2E Test"
    
    log_info "Running E2E test suite in python-worker-1 container..."
    
    # Execute test in container
    if docker exec python-worker-1 python /app/tests/run_e2e_test.py > "$TEST_LOG_FILE" 2>&1; then
        log_success "E2E tests completed successfully"
        log_info "Test log: $TEST_LOG_FILE"
        
        # Display test output
        log_info "Test output:"
        cat "$TEST_LOG_FILE"
    else
        log_error "E2E tests failed"
        log_info "Test output:"
        cat "$TEST_LOG_FILE"
        return 1
    fi
}

################################################################################
# Live Logging
################################################################################

stream_logs() {
    print_section "STEP 6: Live Log Streaming (${LOG_STREAM_DURATION}s)"
    
    log_info "Streaming logs from all services..."
    log_info "Shows the complete distributed transaction flow"
    echo ""
    
    cd "$PROJECT_ROOT"
    
    # Stream logs with timeout
    timeout "$LOG_STREAM_DURATION" docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f \
        --timestamps \
        2>&1 || true
    
    echo ""
    log_success "Log streaming complete"
}

################################################################################
# Teardown
################################################################################

cleanup_services() {
    print_section "STEP 7: Cleanup & Teardown"
    
    log_info "Stopping and removing containers..."
    cd "$PROJECT_ROOT"
    
    if docker-compose -f "$DOCKER_COMPOSE_FILE" down; then
        log_success "Services stopped and removed"
    else
        log_warning "Some services may not have stopped cleanly"
    fi
    
    log_info "Removing unused Docker resources..."
    docker image prune -f --all > /dev/null 2>&1 || true
    docker container prune -f > /dev/null 2>&1 || true
    
    log_success "Cleanup complete"
}

################################################################################
# Summary
################################################################################

print_summary() {
    print_section "E2E TEST EXECUTION COMPLETE"
    
    echo -e "${GREEN}✅ Complete distributed training pipeline executed successfully!${NC}"
    echo ""
    echo "Summary:"
    echo "  - Test Data:     Created"
    echo "  - Docker Build:  Success"
    echo "  - Services:      Running → Tested → Stopped"
    echo "  - E2E Tests:     Passed"
    echo "  - Log File:      $TEST_LOG_FILE"
    echo ""
    echo "What was tested:"
    echo "  1. 🔗 Go Orchestrator RPC server initialization"
    echo "  2. 🔗 Rust Compute Core data preprocessing"
    echo "  3. 🔗 Python AI Service training pipeline"
    echo "  4. 🔗 Zero-copy Cap'n Proto data ingestion"
    echo "  5. 🔗 Gradient aggregation and synchronization"
    echo "  6. 🔗 End-to-end distributed transaction flow"
    echo ""
    echo "Next steps:"
    echo "  - Review test logs: cat $TEST_LOG_FILE"
    echo "  - View architecture: make help"
    echo "  - Run again: ./setup.sh"
    echo ""
}

error_summary() {
    print_section "E2E TEST EXECUTION FAILED"
    
    log_error "Test suite did not complete successfully"
    log_info "Debugging steps:"
    echo "  1. Check error log: cat $TEST_LOG_FILE"
    echo "  2. View service logs: docker-compose -f $DOCKER_COMPOSE_FILE logs"
    echo "  3. Verify services: docker ps -a"
    echo ""
}

################################################################################
# Industry Demo Functions
################################################################################

validate_demo_environment() {
    print_section "🎯 DEMO: Environment Validation"
    
    log_info "Checking for Python3..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 is required for the demo server."
        log_info "Please install Python 3.8+ and try again."
        exit 1
    fi
    log_success "Python3 found: $(python3 --version)"
    
    # Check pip
    if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
        log_error "pip is required for installing demo dependencies."
        exit 1
    fi
    log_success "pip found"
    
    # Check demo directory exists
    if [ ! -d "$DEMO_DIR" ]; then
        log_error "Demo directory not found at $DEMO_DIR"
        exit 1
    fi
    log_success "Demo directory validated"
    
    # Check demo files exist
    if [ ! -f "$DEMO_DIR/server.py" ]; then
        log_error "Demo server not found at $DEMO_DIR/server.py"
        exit 1
    fi
    log_success "Demo server file found"
    
    if [ ! -f "$DEMO_DIR/static/index.html" ]; then
        log_error "Demo dashboard not found at $DEMO_DIR/static/index.html"
        exit 1
    fi
    log_success "Demo dashboard found"
}

install_demo_dependencies() {
    print_section "📦 DEMO: Installing Dependencies"
    
    log_info "Installing web server dependencies..."
    
    if python3 -m pip install -r "$DEMO_DIR/requirements.txt" -q; then
        log_success "Demo dependencies installed successfully"
    else
        log_error "Failed to install demo dependencies"
        exit 1
    fi
}

start_demo_server() {
    print_section "🌐 DEMO: Starting Local Server"
    
    log_info "Starting demo server on port $DEMO_PORT..."
    
    # Export port for server to use
    export DEMO_PORT=$DEMO_PORT
    
    # Start server in background with explicit path (no cd needed)
    python3 "$DEMO_DIR/server.py" &
    SERVER_PID=$!
    
    # Wait for server to start
    log_info "Waiting for server to initialize..."
    sleep 3
    
    # Check if server is running
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        log_error "Demo server failed to start"
        exit 1
    fi
    log_success "Demo server running (PID: $SERVER_PID)"
    
    # Try to open browser
    DEMO_URL="http://localhost:$DEMO_PORT"
    log_info "Opening dashboard in browser: $DEMO_URL"
    
    if command -v open &> /dev/null; then
        open "$DEMO_URL" 2>/dev/null || true
    elif command -v xdg-open &> /dev/null; then
        xdg-open "$DEMO_URL" 2>/dev/null || true
    elif command -v start &> /dev/null; then
        start "$DEMO_URL" 2>/dev/null || true
    else
        log_warning "Could not auto-open browser. Please navigate to: $DEMO_URL"
    fi
    
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  🚀 PANGEA NET DEMO IS RUNNING${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "  Dashboard URL:  $DEMO_URL"
    echo "  Server PID:     $SERVER_PID"
    echo ""
    echo "  Press CTRL+C to stop the demo server."
    echo ""
    
    # Cleanup on exit
    cleanup_demo() {
        echo ""
        log_info "Shutting down demo server..."
        if [ -n "$SERVER_PID" ]; then
            kill "$SERVER_PID" 2>/dev/null || true
        fi
        log_success "Demo server stopped"
        exit 0
    }
    
    trap cleanup_demo INT TERM
    
    # Wait for server process
    wait "$SERVER_PID"
}

run_demo() {
    print_section "🚀 PANGEA NETWORK - INDUSTRY DEMO"
    
    echo "  This demo showcases the Pangea distributed network capabilities"
    echo "  through an interactive web dashboard."
    echo ""
    
    validate_demo_environment
    install_demo_dependencies
    start_demo_server
}

show_help() {
    echo ""
    echo "Usage: ./setup.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --demo      Launch the industry demo dashboard"
    echo "  --help      Show this help message"
    echo "  (no args)   Run the full E2E test suite"
    echo ""
    echo "Examples:"
    echo "  ./setup.sh           # Run E2E tests with Docker"
    echo "  ./setup.sh --demo    # Start the demo web dashboard"
    echo ""
}

################################################################################
# Main Execution Flow
################################################################################

main() {
    print_section "🚀 PANGEA NETWORK - END-TO-END TESTING SETUP"
    
    # Trap errors for cleanup
    trap 'cleanup_services; error_summary; exit 1' ERR INT TERM
    
    validate_environment
    setup_test_data
    build_docker_images
    start_services
    
    # Run tests - capture result but continue for logging
    if run_e2e_test; then
        stream_logs
        cleanup_services
        print_summary
        exit 0
    else
        stream_logs
        cleanup_services
        error_summary
        exit 1
    fi
}

# Run main function
case "${1:-}" in
    --demo)
        run_demo
        ;;
    --help|-h)
        show_help
        exit 0
        ;;
    "")
        main "$@"
        ;;
    *)
        log_error "Unknown option: $1"
        show_help
        exit 1
        ;;
esac
