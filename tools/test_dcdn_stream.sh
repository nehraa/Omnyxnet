#!/bin/bash
# Test DCDN Video Streaming
# 
# This script helps test DCDN video streaming functionality by:
# 1. Generating a test video if needed
# 2. Running the DCDN demo to verify the system
# 3. Providing instructions for streaming tests
#
# Usage:
#   ./tools/test_dcdn_stream.sh [--generate-video] [--run-demo] [--help]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_VIDEO="$PROJECT_ROOT/test_video.mp4"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

show_help() {
    cat << EOF
DCDN Video Streaming Test Script

Usage: $0 [OPTIONS]

Options:
    --generate-video    Generate a new test video
    --run-demo         Run the DCDN Rust demo
    --help             Show this help message

Examples:
    # Generate test video and run demo
    $0 --generate-video --run-demo
    
    # Just generate video
    $0 --generate-video
    
    # Just run demo
    $0 --run-demo

This script helps test DCDN streaming by:
1. Generating a test video (if requested)
2. Running the DCDN demo (if requested)
3. Providing instructions for manual streaming tests

EOF
}

check_dependencies() {
    print_header "Checking Dependencies"
    
    local missing_deps=0
    
    # Check Python
    if command -v python3 &> /dev/null; then
        print_success "Python 3 found: $(python3 --version)"
    else
        print_error "Python 3 not found"
        missing_deps=1
    fi
    
    # Check if we need to generate video
    if [ "$GENERATE_VIDEO" = true ]; then
        # Check OpenCV
        if python3 -c "import cv2" 2>/dev/null; then
            print_success "OpenCV (cv2) found"
        else
            print_error "OpenCV not found. Install with: pip install opencv-python"
            missing_deps=1
        fi
        
        # Check NumPy
        if python3 -c "import numpy" 2>/dev/null; then
            print_success "NumPy found"
        else
            print_error "NumPy not found. Install with: pip install numpy"
            missing_deps=1
        fi
    fi
    
    # Check Rust if we need to run demo
    if [ "$RUN_DEMO" = true ]; then
        if command -v cargo &> /dev/null; then
            print_success "Cargo found: $(cargo --version)"
        else
            print_error "Cargo not found. Install Rust from https://rustup.rs"
            missing_deps=1
        fi
    fi
    
    echo ""
    
    if [ $missing_deps -eq 1 ]; then
        print_error "Missing dependencies. Please install them and try again."
        return 1
    fi
    
    return 0
}

generate_test_video() {
    print_header "Generating Test Video"
    
    if [ -f "$TEST_VIDEO" ]; then
        print_warning "Test video already exists: $TEST_VIDEO"
        read -p "Regenerate? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Skipping video generation"
            return 0
        fi
        rm -f "$TEST_VIDEO"
    fi
    
    print_info "Generating 10-second test video..."
    python3 "$SCRIPT_DIR/generate_test_video.py" "$TEST_VIDEO" 10
    
    if [ -f "$TEST_VIDEO" ]; then
        print_success "Test video generated: $TEST_VIDEO"
        
        # Get file size
        FILE_SIZE=$(du -h "$TEST_VIDEO" | cut -f1)
        print_info "File size: $FILE_SIZE"
        
        return 0
    else
        print_error "Failed to generate test video"
        return 1
    fi
}

run_dcdn_demo() {
    print_header "Running DCDN Demo"
    
    cd "$PROJECT_ROOT/rust"
    
    print_info "Running DCDN system demonstration..."
    print_info "This will show:"
    print_info "  - ChunkStore operations"
    print_info "  - FEC encoding and recovery"
    print_info "  - P2P bandwidth allocation"
    print_info "  - Signature verification"
    echo ""
    
    cargo run --example dcdn_demo
    
    echo ""
    print_success "DCDN demo completed"
    
    cd "$PROJECT_ROOT"
}

run_dcdn_tests() {
    print_header "Running DCDN Tests"
    
    cd "$PROJECT_ROOT/rust"
    
    print_info "Running DCDN test suite..."
    cargo test --test test_dcdn
    
    echo ""
    print_success "DCDN tests completed"
    
    cd "$PROJECT_ROOT"
}

show_streaming_instructions() {
    print_header "DCDN Streaming Instructions"
    
    echo ""
    print_info "Test video location: $TEST_VIDEO"
    echo ""
    
    cat << EOF
To test DCDN video streaming:

METHOD 1: Using Desktop Application
-----------------------------------
1. Launch the desktop app:
   python desktop_app_kivy.py
   (or python desktop_app.py for Tkinter version)

2. Navigate to the DCDN tab

3. On the receiver device:
   - Enter "server" in the Stream Peer IP field
   - Click "Start Stream"

4. On the sender device:
   - Browse to select $TEST_VIDEO
   - Enter receiver's IP address
   - Click "Start Stream"

5. Verify:
   - Video appears on receiver's screen
   - Sender IP is displayed on receiver
   - Stream statistics show packet transmission

METHOD 2: Using Reference Video Implementation
----------------------------------------------
Note: This uses reference implementation for testing

1. On receiver device:
   python python/src/communication/live_video.py true

2. On sender device:
   python python/src/communication/live_video.py false <receiver_ip>

3. This streams webcam video (not the test video file)

METHOD 3: Testing with Tor
--------------------------
1. Start Tor service or Tor Browser

2. In desktop app:
   - Enable "Use Tor Proxy" in Communications tab
   - Click "Test Tor" to verify connection
   - Click "Show My IP" to see your Tor exit node IP

3. Start streaming as above

4. On receiver:
   - Check displayed sender IP
   - Should show Tor exit node IP instead of actual IP

VERIFICATION:
------------
✓ Video plays smoothly on receiver
✓ Sender/receiver IPs are displayed correctly
✓ With Tor: Shows Tor exit node IP
✓ Stream statistics show packet transmission
✓ Frame counter updates in real-time
✓ Color changes are visible (test video cycles colors)

EOF
}

# Main script logic
main() {
    GENERATE_VIDEO=false
    RUN_DEMO=false
    RUN_TESTS=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --generate-video)
                GENERATE_VIDEO=true
                shift
                ;;
            --run-demo)
                RUN_DEMO=true
                shift
                ;;
            --run-tests)
                RUN_TESTS=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # If no options specified, show help
    if [ "$GENERATE_VIDEO" = false ] && [ "$RUN_DEMO" = false ] && [ "$RUN_TESTS" = false ]; then
        show_help
        echo ""
        print_info "Running with default options: --generate-video --run-demo"
        GENERATE_VIDEO=true
        RUN_DEMO=true
    fi
    
    # Check dependencies
    if ! check_dependencies; then
        exit 1
    fi
    
    # Generate video if requested
    if [ "$GENERATE_VIDEO" = true ]; then
        if ! generate_test_video; then
            exit 1
        fi
        echo ""
    fi
    
    # Run demo if requested
    if [ "$RUN_DEMO" = true ]; then
        if ! run_dcdn_demo; then
            exit 1
        fi
        echo ""
    fi
    
    # Run tests if requested
    if [ "$RUN_TESTS" = true ]; then
        if ! run_dcdn_tests; then
            exit 1
        fi
        echo ""
    fi
    
    # Always show streaming instructions
    show_streaming_instructions
    
    echo ""
    print_success "Setup complete! Follow the instructions above to test streaming."
}

main "$@"
