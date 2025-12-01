#!/bin/bash
# Convenience script to start development servers

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 Pangea Net - Development Launcher"
echo "===================================="

case "${1:-help}" in
    "go")
        echo "Starting Go node..."
        export LD_LIBRARY_PATH="$PROJECT_ROOT/rust/target/release:$LD_LIBRARY_PATH"
        cd go && go build -o bin/go-node . && ./bin/go-node "${@:2}"
        ;;
    "python")
        echo "Starting Python AI client..."
        cd python && python main.py "${@:2}"
        ;;
    "monitor")
        echo "Starting network monitor..."
        python tools/load-testing/network_monitor.py "${@:2}"
        ;;
    "docker")
        echo "Starting Docker containers..."
        docker compose -f deployment/compose/docker-compose.yml up -d
        ;;
    "help"|*)
        echo ""
        echo "Usage: $0 <command> [options]"
        echo ""
        echo "Commands:"
        echo "  go [flags]     - Build and run Go node"
        echo "  python [args]  - Run Python AI client"  
        echo "  monitor [opts] - Start network monitoring"
        echo "  docker         - Start Docker containers"
        echo ""
        echo "Examples:"
        echo "  $0 go -node-id=1 -capnp-addr=:8080"
        echo "  $0 python predict --host localhost --port 8080"
        echo "  $0 monitor --nodes localhost:8080 localhost:8081"
        echo "  $0 docker"
        ;;
esac