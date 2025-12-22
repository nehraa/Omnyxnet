#!/usr/bin/env bash
# =============================================================================
# GUI Test Network Management Script
# =============================================================================
# Manages a multi-node Docker network for GUI testing
#
# Usage:
#   ./scripts/gui_test_network.sh start   - Start 5-node network
#   ./scripts/gui_test_network.sh stop    - Stop network
#   ./scripts/gui_test_network.sh status  - Show network status
#   ./scripts/gui_test_network.sh logs    - Show logs from all nodes
#   ./scripts/gui_test_network.sh addrs   - Show multiaddrs of all nodes
#   ./scripts/gui_test_network.sh connect - Instructions for GUI connection
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.gui-test.yml"

# Functions
print_header() {
    echo -e "${BLUE}===================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}===================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

check_docker() {
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    else
        print_error "Docker Compose not found. Please install Docker and Docker Compose."
        exit 1
    fi
}

start_network() {
    print_header "Starting 5-Node GUI Test Network"
    
    cd "$PROJECT_ROOT"
    
    print_info "Building Go node images..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" build
    
    print_info "Starting network..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d
    
    print_info "Waiting for nodes to be healthy..."
    sleep 5
    
    # Check health
    for i in {1..30}; do
        if $DOCKER_COMPOSE -f "$COMPOSE_FILE" ps | grep -q "healthy"; then
            print_success "Nodes are starting up..."
            break
        fi
        sleep 1
    done
    
    print_success "Network started successfully!"
    echo ""
    print_info "Container Status:"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" ps
    echo ""
    print_info "To connect desktop GUI, run:"
    echo -e "${GREEN}  python3 desktop/desktop_app_kivy.py${NC}"
    echo ""
    print_info "GUI will auto-connect to localhost:8080 (node1)"
    echo ""
    print_info "To view logs:"
    echo -e "${GREEN}  ./scripts/gui_test_network.sh logs${NC}"
    echo ""
    print_info "To show multiaddrs:"
    echo -e "${GREEN}  ./scripts/gui_test_network.sh addrs${NC}"
}

stop_network() {
    print_header "Stopping GUI Test Network"
    
    cd "$PROJECT_ROOT"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" down
    
    print_success "Network stopped"
}

show_status() {
    print_header "Network Status"
    
    cd "$PROJECT_ROOT"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" ps
    
    echo ""
    print_info "Network Health:"
    for node in node1 node2 node3 node4 node5; do
        container="wgt-gui-$node"
        if docker ps --filter "name=$container" --filter "health=healthy" | grep -q "$container"; then
            print_success "$node (172.30.0.$((9 + ${node#node}))): healthy"
        elif docker ps --filter "name=$container" --filter "health=unhealthy" | grep -q "$container"; then
            print_error "$node: unhealthy"
        elif docker ps --filter "name=$container" | grep -q "$container"; then
            print_info "$node: starting..."
        else
            print_error "$node: not running"
        fi
    done
}

show_logs() {
    print_header "Network Logs (Ctrl+C to exit)"
    
    cd "$PROJECT_ROOT"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" logs -f --tail=50
}

show_multiaddrs() {
    print_header "Node Multiaddrs"
    
    cd "$PROJECT_ROOT"
    
    echo ""
    print_info "Extracting multiaddrs from container logs..."
    echo ""
    
    for node in node1 node2 node3 node4 node5; do
        container="wgt-gui-$node"
        node_num="${node#node}"
        ip="172.30.0.$((9 + node_num))"
        
        echo -e "${BLUE}Node $node_num (IP: $ip):${NC}"
        
        # Try to extract multiaddr from logs
        multiaddr=$($DOCKER_COMPOSE -f "$COMPOSE_FILE" logs "$node" 2>&1 | grep -oP '/ip4/[0-9.]+/tcp/[0-9]+/p2p/[a-zA-Z0-9]+' | head -1 || echo "")
        
        if [ -n "$multiaddr" ]; then
            # Replace 0.0.0.0 or 127.0.0.1 with container IP
            multiaddr=$(echo "$multiaddr" | sed "s|/ip4/0.0.0.0|/ip4/$ip|g" | sed "s|/ip4/127.0.0.1|/ip4/$ip|g")
            echo -e "${GREEN}  $multiaddr${NC}"
        else
            echo -e "${YELLOW}  Multiaddr not yet available (node may still be starting)${NC}"
        fi
        
        # Also show localhost mapping for GUI
        if [ "$node" == "node1" ]; then
            echo -e "${YELLOW}  For GUI: Use localhost:8080 (automatically mapped)${NC}"
        fi
        echo ""
    done
    
    print_info "Copy and paste any multiaddr (except node1) into the GUI 'Peer Connection' field"
}

show_connect_instructions() {
    print_header "GUI Connection Instructions"
    
    echo ""
    echo "1. Start the GUI:"
    echo -e "   ${GREEN}python3 desktop/desktop_app_kivy.py${NC}"
    echo ""
    echo "2. The GUI will auto-connect to localhost:8080 (node1)"
    echo ""
    echo "3. To connect to other nodes as peers:"
    echo "   a. Get multiaddrs:"
    echo -e "      ${GREEN}./scripts/gui_test_network.sh addrs${NC}"
    echo "   b. Copy a multiaddr (e.g., for node2)"
    echo "   c. Paste it in the 'Peer Connection' field in the GUI"
    echo "   d. Click 'Connect to Peer'"
    echo ""
    echo "4. Test features:"
    echo "   - Node Management: List nodes, view info, check health"
    echo "   - Compute Tasks: Submit jobs, list workers, check status"
    echo "   - File Operations: Upload/download files across the network"
    echo "   - Communications: Test P2P, ping nodes, check network health"
    echo "   - Network Info: View peers, topology, statistics"
    echo ""
    print_info "All 5 nodes will discover each other via mDNS automatically"
    print_info "You can connect to any node and test features through the GUI"
}

# Main script
case "${1:-}" in
    start)
        check_docker
        start_network
        ;;
    stop)
        check_docker
        stop_network
        ;;
    status)
        check_docker
        show_status
        ;;
    logs)
        check_docker
        show_logs
        ;;
    addrs)
        check_docker
        show_multiaddrs
        ;;
    connect)
        show_connect_instructions
        ;;
    *)
        print_header "GUI Test Network Management"
        echo ""
        echo "Usage: $0 {start|stop|status|logs|addrs|connect}"
        echo ""
        echo "Commands:"
        echo "  start    - Start 5-node network"
        echo "  stop     - Stop network"
        echo "  status   - Show network status"
        echo "  logs     - Show logs from all nodes (follow mode)"
        echo "  addrs    - Show multiaddrs of all nodes"
        echo "  connect  - Show GUI connection instructions"
        echo ""
        exit 1
        ;;
esac
