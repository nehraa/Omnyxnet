#!/bin/bash

echo "🚀 Pangea Net - Load Testing Suite"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if containers are running
check_containers() {
    echo -e "${BLUE}📋 Checking container status...${NC}"
    
    running_containers=$(docker compose ps -q 2>/dev/null | wc -l)
    total_containers=$(docker compose config --services 2>/dev/null | wc -l)
    
    echo "Running containers: $running_containers / $total_containers"
    
    if [ $running_containers -eq 0 ]; then
        echo -e "${RED}❌ No containers are running!${NC}"
        echo "Starting containers with docker compose up -d"
        docker compose up -d
        sleep 10
    elif [ $running_containers -lt $total_containers ]; then
        echo -e "${YELLOW}⚠️  Some containers are not running${NC}"
        docker compose ps
    else
        echo -e "${GREEN}✅ All containers are running${NC}"
    fi
}

# Function to wait for services to be ready
wait_for_services() {
    echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
    
    max_attempts=30
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        ready_count=0
        
        # Check each port
        for port in 8080 8081 8082; do
            if nc -z localhost $port 2>/dev/null; then
                ready_count=$((ready_count + 1))
            fi
        done
        
        if [ $ready_count -eq 3 ]; then
            echo -e "${GREEN}✅ All services are ready!${NC}"
            return 0
        fi
        
        echo "Services ready: $ready_count/3 (attempt $((attempt + 1))/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}❌ Services failed to start within timeout${NC}"
    return 1
}

# Function to run basic connectivity test
basic_test() {
    echo -e "${BLUE}🔧 Running basic connectivity test...${NC}"
    
    python3 -c "
import sys
sys.path.insert(0, 'python/src')
from client.go_client import GoNodeClient

success = 0
total = 3

for port in [8080, 8081, 8082]:
    try:
        client = GoNodeClient('localhost', port)
        if client.connect():
            nodes = client.get_all_nodes()
            print(f'✅ Node localhost:{port} - Connected ({len(nodes)} peers)')
            success += 1
        else:
            print(f'❌ Node localhost:{port} - Connection failed')
    except Exception as e:
        print(f'❌ Node localhost:{port} - Error: {e}')

print(f'\\nBasic Test Result: {success}/{total} nodes responding')
" || echo -e "${RED}❌ Basic test failed${NC}"
}

# Function to run performance monitoring
performance_test() {
    echo -e "${BLUE}📊 Running performance monitoring (60 seconds)...${NC}"
    
    cd /home/abhinav/Desktop/WGT && python3 tools/load-testing/network_monitor.py \
        --nodes localhost:8080 localhost:8081 localhost:8082 \
        --monitor 60 \
        --interval 1.0 \
        --save "performance_test_$(date +%s).json"
}

# Function to run stress test
stress_test() {
    echo -e "${BLUE}💥 Running stress test...${NC}"
    
    cd /home/abhinav/Desktop/WGT && python3 tools/load-testing/network_monitor.py \
        --nodes localhost:8080 localhost:8081 localhost:8082 \
        --stress \
        --save "stress_test_$(date +%s).json"
}

# Function to run scale test
scale_test() {
    echo -e "${BLUE}📈 Running scale test with docker-compose.test.yml...${NC}"
    
    # Stop current containers
    docker compose down
    
    # Start with test configuration (more nodes)
    docker compose -f ../../deployment/compose/docker-compose.test.yml up -d
    
    # Wait for services
    echo "Waiting for scale test services to start..."
    sleep 30
    
    # Generate node list for scale test
    nodes=""
    for port in {8080..8089}; do
        nodes="$nodes localhost:$port"
    done
    
    echo "Testing with 10 nodes..."
    cd /home/abhinav/Desktop/WGT && python3 tools/load-testing/network_monitor.py \
        --nodes $nodes \
        --monitor 120 \
        --interval 2.0 \
        --save "scale_test_$(date +%s).json"
    
    # Cleanup
    docker compose -f ../../deployment/compose/docker-compose.test.yml down
    docker compose -f ../../deployment/compose/docker-compose.yml up -d
}

# Function to analyze logs
analyze_logs() {
    echo -e "${BLUE}📝 Analyzing container logs...${NC}"
    
    echo "Recent errors in Go nodes:"
    docker compose logs --tail=50 go-node-1 go-node-2 go-node-3 2>/dev/null | grep -i error || echo "No errors found"
    
    echo -e "\nRecent warnings:"
    docker compose logs --tail=50 2>/dev/null | grep -i warn || echo "No warnings found"
    
    echo -e "\nConnection statistics:"
    docker compose logs --tail=100 2>/dev/null | grep -E "(connected|disconnected|peer)" | tail -10
}

# Function to show resource usage
resource_usage() {
    echo -e "${BLUE}💻 Container resource usage:${NC}"
    
    echo "CPU and Memory usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
    
    echo -e "\nDisk usage:"
    docker system df
}

# Function to cleanup
cleanup() {
    echo -e "${BLUE}🧹 Cleaning up...${NC}"
    
    docker compose down 2>/dev/null || true
    docker system prune -f
    
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

# Main menu
show_menu() {
    echo -e "\n${YELLOW}Choose a test to run:${NC}"
    echo "1) Basic connectivity test"
    echo "2) Performance monitoring (60s)"
    echo "3) Stress test (find limits)"
    echo "4) Scale test (10 nodes)"
    echo "5) Analyze logs"
    echo "6) Resource usage"
    echo "7) Full test suite (all tests)"
    echo "8) Cleanup and exit"
    echo "9) Exit"
    echo -n "Enter choice [1-9]: "
}

# Full test suite
full_test_suite() {
    echo -e "${YELLOW}🧪 Running full test suite...${NC}"
    
    basic_test
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    performance_test
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    stress_test
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    analyze_logs
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    resource_usage
    
    echo -e "\n${GREEN}🎉 Full test suite completed!${NC}"
}

# Main execution
main() {
    # Initial setup
    check_containers
    wait_for_services || exit 1
    
    if [ $# -eq 0 ]; then
        # Interactive mode
        while true; do
            show_menu
            read -r choice
            
            case $choice in
                1) basic_test ;;
                2) performance_test ;;
                3) stress_test ;;
                4) scale_test ;;
                5) analyze_logs ;;
                6) resource_usage ;;
                7) full_test_suite ;;
                8) cleanup; exit 0 ;;
                9) exit 0 ;;
                *) echo -e "${RED}Invalid option. Please try again.${NC}" ;;
            esac
            
            echo -e "\n${YELLOW}Press Enter to continue...${NC}"
            read -r
        done
    else
        # Command line mode
        case $1 in
            basic|connectivity) basic_test ;;
            performance|perf) performance_test ;;
            stress) stress_test ;;
            scale) scale_test ;;
            logs) analyze_logs ;;
            resources|stats) resource_usage ;;
            full|all) full_test_suite ;;
            cleanup) cleanup ;;
            *) 
                echo "Usage: $0 [basic|performance|stress|scale|logs|resources|full|cleanup]"
                echo "Run without arguments for interactive mode"
                exit 1
                ;;
        esac
    fi
}

# Run main function
main "$@"