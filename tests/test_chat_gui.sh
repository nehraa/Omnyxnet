#!/bin/bash
#
# Simple Chat Test Script
# Tests the improved chat functionality between two nodes
#

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==========================================="
echo "  CHAT FUNCTIONALITY TEST"
echo "==========================================="
echo ""
echo "This script will help you test the improved chat system."
echo ""
echo "Prerequisites:"
echo "  1. Python dependencies installed (kivy, kivymd, capnp)"
echo "  2. Go node built (go/bin/go-node)"
echo "  3. Two machines on the same network OR two terminal windows"
echo ""
echo "Test Procedure:"
echo ""
echo "=== MACHINE A (or Terminal 1) ==="
echo "1. Run: python3 desktop/desktop_app_kivy.py"
echo "2. Click 'Connect to Node' (localhost:8080)"
echo "3. Go to 'Communications' tab"
echo "4. Click green 'Show My IP' button"
echo "5. Note the IP address shown"
echo "6. Share this IP with Machine B"
echo "7. Enter Machine B's IP in 'Peer IP address' field"
echo "8. Click 'Start Chat Session'"
echo "9. Wait for connection confirmation"
echo ""
echo "=== MACHINE B (or Terminal 2) ==="
echo "1. Run: python3 desktop/desktop_app_kivy.py"
echo "2. Click 'Connect to Node' (localhost:8081 if same machine, 8080 if different)"
echo "3. Go to 'Communications' tab"
echo "4. Click green 'Show My IP' button"
echo "5. Share this IP with Machine A"
echo "6. Enter Machine A's IP in 'Peer IP address' field"
echo "7. Click 'Start Chat Session'"
echo "8. Wait for connection confirmation"
echo ""
echo "=== TESTING MESSAGE EXCHANGE ==="
echo "Machine A:"
echo "  - Type 'Hello from A' in message field"
echo "  - Click 'Send Message'"
echo "  - Check output area for sent confirmation"
echo ""
echo "Machine B:"
echo "  - Should see 'Peer (...): Hello from A' appear in output"
echo "  - Type 'Hello from B' and send"
echo ""
echo "Machine A:"
echo "  - Should see 'Peer (...): Hello from B' appear in output"
echo ""
echo "=== EXPECTED RESULTS ==="
echo "✅ Both nodes show 'Chat is now ACTIVE'"
echo "✅ Sent messages appear as 'You: <message>'"
echo "✅ Received messages appear as 'Peer (...): <message>'"
echo "✅ Messages appear in BOTH terminal logs AND GUI output"
echo ""
echo "=== TROUBLESHOOTING ==="
echo "If messages don't appear:"
echo "  1. Check both nodes clicked 'Start Chat Session'"
echo "  2. Verify IP addresses are correct (use 'Show My IP')"
echo "  3. Check firewall allows port 9999"
echo "  4. Confirm Go node is running (green 'Connected' status)"
echo "  5. Look for error messages in terminal"
echo ""
echo "=== AUTOMATED SINGLE-MACHINE TEST ==="
read -p "Run automated test on this machine? (y/N): " run_auto

if [ "$run_auto" = "y" ] || [ "$run_auto" = "Y" ]; then
    echo ""
    echo "Starting automated test..."
    echo ""
    
    # Check if Go node exists
    if [ ! -f "go/bin/go-node" ]; then
        echo "❌ Go node not found. Building..."
        cd go
        go build -o bin/go-node .
        cd ..
    fi
    
    # Set library path
    export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$LD_LIBRARY_PATH"
    export DYLD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$DYLD_LIBRARY_PATH"
    
    # Create log directory
    LOG_DIR="$HOME/.wgt/test_logs"
    mkdir -p "$LOG_DIR"
    
    # Start first Go node
    echo "Starting Node A on port 8080..."
    cd go
    ./bin/go-node -node-id=1 -capnp-addr=:8080 -libp2p=true -libp2p-port=9081 -local > "$LOG_DIR/node_a.log" 2>&1 &
    NODE_A_PID=$!
    cd ..
    sleep 2
    
    # Start second Go node  
    echo "Starting Node B on port 8081..."
    cd go
    ./bin/go-node -node-id=2 -capnp-addr=:8081 -libp2p=true -libp2p-port=9082 -local > "$LOG_DIR/node_b.log" 2>&1 &
    NODE_B_PID=$!
    cd ..
    sleep 2
    
    echo ""
    echo "✅ Both Go nodes started"
    echo "   Node A: localhost:8080 (PID: $NODE_A_PID)"
    echo "   Node B: localhost:8081 (PID: $NODE_B_PID)"
    echo ""
    echo "Now you can:"
    echo "  1. Open desktop_app_kivy.py"
    echo "  2. Connect to localhost:8080"
    echo "  3. Follow the test procedure above"
    echo ""
    echo "To stop the nodes:"
    echo "  kill $NODE_A_PID $NODE_B_PID"
    echo ""
    echo "Logs:"
    echo "  Node A: $LOG_DIR/node_a.log"
    echo "  Node B: $LOG_DIR/node_b.log"
    echo ""
    
    # Save PIDs for cleanup
    echo "$NODE_A_PID" > "$LOG_DIR/test_node_a.pid"
    echo "$NODE_B_PID" > "$LOG_DIR/test_node_b.pid"
    
    read -p "Press Enter when done testing to stop nodes..."
    
    # Cleanup
    if [ -f "$LOG_DIR/test_node_a.pid" ]; then
        NODE_A_PID=$(cat "$LOG_DIR/test_node_a.pid")
        kill $NODE_A_PID 2>/dev/null || true
        rm "$LOG_DIR/test_node_a.pid"
    fi
    
    if [ -f "$LOG_DIR/test_node_b.pid" ]; then
        NODE_B_PID=$(cat "$LOG_DIR/test_node_b.pid")
        kill $NODE_B_PID 2>/dev/null || true
        rm "$LOG_DIR/test_node_b.pid"
    fi
    
    echo "✅ Test nodes stopped"
fi

echo ""
echo "Test script complete."
