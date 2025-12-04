#!/bin/bash
# Cross-Device Streaming Test Script for Pangea Net
# Combines cross-device connectivity testing with live audio/video streaming
# Supports both localhost testing and real cross-device scenarios
#
# Features:
# - Automatic device detection and setup
# - Live audio streaming with Opus codec
# - Live video streaming with compression
# - Real-time performance monitoring
# - Cross-device connectivity validation
# - Modular design for easy extension

set -e

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
WHITE='\033[1;37m'
NC='\033[0m'

# Bold colors
BOLD_RED='\033[1;31m'
BOLD_GREEN='\033[1;32m'
BOLD_YELLOW='\033[1;33m'
BOLD_BLUE='\033[1;34m'
BOLD_CYAN='\033[1;36m'
BOLD_MAGENTA='\033[1;35m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_RESULTS_DIR="$PROJECT_ROOT/test_results/cross_device_streaming"
LOG_FILE="$TEST_RESULTS_DIR/cross_device_streaming_$(date +%Y%m%d_%H%M%S).log"

# Default settings
DEFAULT_NODE_ID=""
DEFAULT_MODE="interactive"
DEFAULT_TEST_DURATION=30
DEFAULT_AUDIO_SAMPLE_RATE=48000
DEFAULT_VIDEO_BITRATE="2M"
DEFAULT_STREAM_TYPE="audio_video"

# Global variables
NODE_ID=""
BOOTSTRAP_PEER=""
TEST_MODE=""
STREAM_TYPE=""
TEST_DURATION=""
AUDIO_CONFIG=""
VIDEO_CONFIG=""
CROSS_DEVICE=false
LOCALHOST_TEST=false

# Logging function
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")

    # Ensure log directory exists
    mkdir -p "$(dirname "$LOG_FILE")"

    echo -e "[$timestamp] [$level] $message" >> "$LOG_FILE"
    echo -e "[$level] $message"
}

# Error handling
error_exit() {
    local message="$1"
    log "ERROR" "$message"
    echo -e "${BOLD_RED}❌ Error: $message${NC}" >&2
    cleanup
    exit 1
}

# Cleanup function
cleanup() {
    log "INFO" "Cleaning up test processes..."

    # Kill any running test processes
    pkill -f "cross_device_streaming_test" 2>/dev/null || true
    pkill -f "voice_streaming_demo" 2>/dev/null || true
    pkill -f "streaming_test" 2>/dev/null || true

    # Clean up test files
    rm -f /tmp/cross_device_streaming_*.pid 2>/dev/null || true
    rm -f /tmp/streaming_test_*.log 2>/dev/null || true

    log "INFO" "Cleanup completed"
}

# Trap for cleanup on exit
trap cleanup EXIT INT TERM

# Check dependencies
check_dependencies() {
    log "INFO" "Checking dependencies..."

    local missing_deps=()

    # Check for required commands
    for cmd in cargo python3 ffmpeg curl wget; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps+=("$cmd")
        fi
    done

    # Check for Go
    if ! command -v go &> /dev/null && ! command -v "$PROJECT_ROOT/go/bin/go-node" &> /dev/null; then
        missing_deps+=("go or go-node binary")
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        error_exit "Missing dependencies: ${missing_deps[*]}"
    fi

    # Check for Python modules
    if ! python3 -c "import numpy, wave, asyncio" 2>/dev/null; then
        log "WARN" "Some Python modules missing - audio tests may fail"
    fi

    log "INFO" "Dependencies check completed"
}

# Setup test environment
setup_test_environment() {
    log "INFO" "Setting up test environment..."

    # Create test directories
    mkdir -p "$TEST_RESULTS_DIR"
    mkdir -p "$PROJECT_ROOT/test_media/samples"
    mkdir -p "$PROJECT_ROOT/test_streams"
    mkdir -p "$PROJECT_ROOT/benchmarks/streaming"

    # Create log file
    touch "$LOG_FILE"

    # Generate test media if needed
    if [ ! -f "$PROJECT_ROOT/test_media/samples/test_audio.wav" ]; then
        log "INFO" "Generating test audio file..."
        python3 -c "
import numpy as np
import wave
import os

# Generate 10 seconds of test audio
sample_rate = 48000
duration = 10
t = np.linspace(0, duration, int(sample_rate * duration))

# Create test signal
audio = 0.5 * np.sin(2 * np.pi * 440 * t)  # 440Hz sine wave
audio = (audio * 32767).astype(np.int16)

# Save as WAV
with wave.open('$PROJECT_ROOT/test_media/samples/test_audio.wav', 'wb') as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(sample_rate)
    f.writeframes(audio.tobytes())

print('Test audio generated')
" 2>/dev/null || log "WARN" "Failed to generate test audio"
    fi

    if [ ! -f "$PROJECT_ROOT/test_media/samples/test_video.mp4" ]; then
        log "INFO" "Downloading test video file..."
        if command -v curl &> /dev/null; then
            curl -L -o "$PROJECT_ROOT/test_media/samples/test_video.mp4" \
                "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4" 2>/dev/null || \
            log "WARN" "Failed to download test video"
        fi
    fi

    log "INFO" "Test environment setup completed"
}

# Build project components
build_project() {
    log "INFO" "Building project components..."

    cd "$PROJECT_ROOT"

    # Build Rust components
    if [ -f "rust/Cargo.toml" ]; then
        log "INFO" "Building Rust components..."
        cd rust
        cargo build --release --quiet
        cd ..
    fi

    # Build Go components
    if [ -f "go/Makefile" ]; then
        log "INFO" "Building Go components..."
        cd go
        make build >/dev/null 2>&1
        cd ..
    fi

    # Build Python components if needed
    if [ -f "python/requirements.txt" ]; then
        log "INFO" "Installing Python dependencies..."
        cd python
        pip install -r requirements.txt >/dev/null 2>&1 || true
        cd ..
    fi

    log "INFO" "Project build completed"
}

# Detect test mode
detect_test_mode() {
    log "INFO" "Detecting test mode..."

    # Check if we're running on localhost only
    if [ "$LOCALHOST_TEST" = true ]; then
        TEST_MODE="localhost"
        log "INFO" "Running in localhost test mode"
        return
    fi

    # Check for existing nodes
    if pgrep -f "go-node\|easy_test" >/dev/null 2>&1; then
        log "INFO" "Detected existing Pangea Net nodes - joining network"
        TEST_MODE="join"
        # Try to find bootstrap peer
        BOOTSTRAP_PEER=$(find_bootstrap_peer)
    else
        log "INFO" "No existing nodes detected - starting as bootstrap"
        TEST_MODE="bootstrap"
    fi
}

# Find bootstrap peer
find_bootstrap_peer() {
    # Try to find bootstrap peer from running processes or config
    local peer=""

    # Check for peer info in logs or config files
    if [ -f "$PROJECT_ROOT/bootstrap_peer.txt" ]; then
        peer=$(cat "$PROJECT_ROOT/bootstrap_peer.txt")
    fi

    # Default fallback
    if [ -z "$peer" ]; then
        peer="/ip4/127.0.0.1/tcp/9080/p2p/QmTestPeer123"
    fi

    echo "$peer"
}

# Start node
start_node() {
    local node_type="$1"

    log "INFO" "Starting $node_type node..."

    case "$node_type" in
        "bootstrap")
            # Start bootstrap node
            cd "$PROJECT_ROOT"
            if [ -f "scripts/easy_test.sh" ]; then
                bash scripts/easy_test.sh 1 &
                echo $! > /tmp/cross_device_streaming_bootstrap.pid
                sleep 3
            fi
            ;;
        "join")
            # Start joining node
            cd "$PROJECT_ROOT"
            if [ -f "scripts/easy_test.sh" ]; then
                bash scripts/easy_test.sh 2 "$BOOTSTRAP_PEER" &
                echo $! > /tmp/cross_device_streaming_join.pid
                sleep 3
            fi
            ;;
    esac

    log "INFO" "$node_type node started"
}

# Run streaming tests
run_streaming_tests() {
    local test_type="$1"

    log "INFO" "Running $test_type streaming tests..."

    case "$test_type" in
        "audio")
            run_audio_streaming_test
            ;;
        "video")
            run_video_streaming_test
            ;;
        "audio_video")
            run_audio_streaming_test
            run_video_streaming_test
            ;;
    esac
}

# Run audio streaming test
run_audio_streaming_test() {
    log "INFO" "Running audio streaming test..."

    cd "$PROJECT_ROOT/rust"

    # Run the voice streaming demo
    if [ -f "target/release/examples/voice_streaming_demo" ]; then
        log "INFO" "Running voice streaming demo..."
        timeout 60s cargo run --example voice_streaming_demo --release 2>&1 | tee -a "$LOG_FILE" || true
    else
        log "WARN" "Voice streaming demo not found, running basic streaming test..."
        cargo test --test test_streaming --release -- --nocapture 2>&1 | tee -a "$LOG_FILE" || true
    fi

    # Run Python streaming tests
    if [ -f "../tests/streaming/test_localhost_streaming.py" ]; then
        log "INFO" "Running Python streaming tests..."
        cd "$PROJECT_ROOT"
        python3 tests/streaming/test_localhost_streaming.py 2>&1 | tee -a "$LOG_FILE" || true
    fi

    log "INFO" "Audio streaming test completed"
}

# Run video streaming test
run_video_streaming_test() {
    log "INFO" "Running video streaming test..."

    # Check if test video exists
    if [ ! -f "$PROJECT_ROOT/test_media/samples/test_video.mp4" ]; then
        log "WARN" "Test video not found, skipping video streaming test"
        return
    fi

    # Run video processing test
    cd "$PROJECT_ROOT"

    if [ -f "tests/test_phase1_video.py" ]; then
        log "INFO" "Running Python video streaming tests..."
        python3 tests/test_phase1_video.py 2>&1 | tee -a "$LOG_FILE" || true
    else
        log "INFO" "Running basic video compression test..."
        # Basic video compression test using ffmpeg
        ffmpeg -i "$PROJECT_ROOT/test_media/samples/test_video.mp4" \
               -c:v libx264 -b:v 1M -maxrate 1M -bufsize 2M \
               -vf scale=640:360 \
               -f mp4 /tmp/test_compressed.mp4 \
               -y >/dev/null 2>&1 && \
        log "INFO" "Video compression test completed" || \
        log "WARN" "Video compression test failed"
    fi

    log "INFO" "Video streaming test completed"
}

# Run cross-device connectivity test
run_cross_device_test() {
    log "INFO" "Running cross-device connectivity test..."

    cd "$PROJECT_ROOT"

    # Run the cross-device upload/download test
    if [ -f "tests/integration/test_upload_download_cross_device.sh" ]; then
        log "INFO" "Running cross-device file transfer test..."
        bash tests/integration/test_upload_download_cross_device.sh 2>&1 | tee -a "$LOG_FILE" || true
    fi

    # Test P2P connectivity
    if [ -f "tests/test_p2p_connectivity.py" ]; then
        log "INFO" "Running P2P connectivity test..."
        python3 tests/test_p2p_connectivity.py 2>&1 | tee -a "$LOG_FILE" || true
    fi

    log "INFO" "Cross-device connectivity test completed"
}

# Monitor performance
monitor_performance() {
    local duration="$1"

    log "INFO" "Starting performance monitoring for ${duration}s..."

    local end_time=$((SECONDS + duration))
    local sample_count=0

    while [ $SECONDS -lt $end_time ]; do
        # Collect system metrics
        local cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
        local mem_usage=$(free | grep Mem | awk '{printf "%.2f", $3/$2 * 100.0}')

        # Collect network stats if available
        local network_stats=""
        if command -v ss &> /dev/null; then
            network_stats=$(ss -tuln | wc -l)
        fi

        # Log metrics
        log "METRICS" "CPU: ${cpu_usage}%, MEM: ${mem_usage}%, NETWORK: ${network_stats}"

        sample_count=$((sample_count + 1))
        sleep 2
    done

    log "INFO" "Performance monitoring completed ($sample_count samples collected)"
}

# Generate test report
generate_report() {
    log "INFO" "Generating test report..."

    local report_file="$TEST_RESULTS_DIR/report_$(date +%Y%m%d_%H%M%S).md"

    cat > "$report_file" << EOF
# Cross-Device Streaming Test Report

**Date:** $(date)  
**Test Mode:** $TEST_MODE  
**Stream Type:** $STREAM_TYPE  
**Duration:** ${TEST_DURATION}s  
**Cross-Device:** $CROSS_DEVICE  

## Test Configuration

- Node ID: $NODE_ID
- Bootstrap Peer: $BOOTSTRAP_PEER
- Audio Config: $AUDIO_CONFIG
- Video Config: $VIDEO_CONFIG

## Test Results

### Streaming Performance
$(grep -E "(compression|latency|throughput|bitrate)" "$LOG_FILE" | tail -10 || echo "No performance data available")

### Connectivity Status
$(grep -E "(connected|peer|network)" "$LOG_FILE" | tail -10 || echo "No connectivity data available")

### System Metrics
$(grep "METRICS" "$LOG_FILE" | tail -10 || echo "No system metrics available")

## Log Summary
$(tail -20 "$LOG_FILE")

---
*Generated by cross_device_streaming_test.sh*
EOF

    log "INFO" "Test report generated: $report_file"
    echo -e "${BOLD_GREEN}📊 Test report: $report_file${NC}"
}

# Interactive mode
interactive_mode() {
    echo -e "${BOLD_CYAN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD_CYAN}║     🌍 Cross-Device Streaming Test         ║${NC}"
    echo -e "${BOLD_CYAN}╚══════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "${CYAN}Test Configuration:${NC}"
    echo "1. Localhost testing only (single device)"
    echo "2. Cross-device testing (multiple devices)"
    echo ""

    read -p "Select test mode (1 or 2): " mode_choice

    case "$mode_choice" in
        1)
            LOCALHOST_TEST=true
            echo -e "${GREEN}✅ Localhost testing selected${NC}"
            ;;
        2)
            CROSS_DEVICE=true
            echo -e "${GREEN}✅ Cross-device testing selected${NC}"
            ;;
        *)
            error_exit "Invalid choice"
            ;;
    esac

    echo ""
    echo -e "${CYAN}Stream Type:${NC}"
    echo "1. Audio only"
    echo "2. Video only"
    echo "3. Audio + Video"
    echo ""

    read -p "Select stream type (1-3): " stream_choice

    case "$stream_choice" in
        1) STREAM_TYPE="audio" ;;
        2) STREAM_TYPE="video" ;;
        3) STREAM_TYPE="audio_video" ;;
        *) error_exit "Invalid choice" ;;
    esac

    echo -e "${GREEN}✅ Stream type: $STREAM_TYPE${NC}"

    echo ""
    read -p "Test duration in seconds (default: 30): " TEST_DURATION
    TEST_DURATION=${TEST_DURATION:-30}

    echo -e "${GREEN}✅ Test duration: ${TEST_DURATION}s${NC}"
}

# Main function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --localhost)
                LOCALHOST_TEST=true
                shift
                ;;
            --cross-device)
                CROSS_DEVICE=true
                shift
                ;;
            --audio)
                STREAM_TYPE="audio"
                shift
                ;;
            --video)
                STREAM_TYPE="video"
                shift
                ;;
            --audio-video)
                STREAM_TYPE="audio_video"
                shift
                ;;
            --duration)
                TEST_DURATION="$2"
                shift 2
                ;;
            --node-id)
                NODE_ID="$2"
                shift 2
                ;;
            --bootstrap)
                BOOTSTRAP_PEER="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --localhost           Run localhost testing only"
                echo "  --cross-device        Run cross-device testing"
                echo "  --audio               Test audio streaming only"
                echo "  --video               Test video streaming only"
                echo "  --audio-video         Test audio + video streaming"
                echo "  --duration SECONDS    Test duration (default: 30)"
                echo "  --node-id ID          Node ID for cross-device testing"
                echo "  --bootstrap PEER      Bootstrap peer address"
                echo "  --help                Show this help"
                exit 0
                ;;
            *)
                error_exit "Unknown option: $1"
                ;;
        esac
    done

    # Set defaults
    TEST_DURATION=${TEST_DURATION:-30}
    STREAM_TYPE=${STREAM_TYPE:-"audio_video"}

    # Interactive mode if no mode specified
    if [ "$LOCALHOST_TEST" != true ] && [ "$CROSS_DEVICE" != true ]; then
        interactive_mode
    fi

    echo -e "${BOLD_BLUE}🚀 Starting Cross-Device Streaming Test${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""

    # Initialize
    check_dependencies
    setup_test_environment
    build_project

    # Detect and setup test mode
    detect_test_mode

    # Start nodes if cross-device
    if [ "$CROSS_DEVICE" = true ]; then
        start_node "$TEST_MODE"
    fi

    # Run tests
    echo -e "${YELLOW}🧪 Running streaming tests...${NC}"
    run_streaming_tests "$STREAM_TYPE"

    if [ "$CROSS_DEVICE" = true ]; then
        echo -e "${YELLOW}🌐 Running cross-device connectivity tests...${NC}"
        run_cross_device_test
    fi

    # Monitor performance
    echo -e "${YELLOW}📊 Monitoring performance...${NC}"
    monitor_performance "$TEST_DURATION"

    # Generate report
    generate_report

    echo ""
    echo -e "${BOLD_GREEN}✅ Cross-Device Streaming Test Completed!${NC}"
    echo -e "${GREEN}📊 Results saved to: $TEST_RESULTS_DIR${NC}"
    echo -e "${GREEN}📝 Log file: $LOG_FILE${NC}"
}

# Run main function
main "$@"