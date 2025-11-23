#!/bin/bash
# Scale testing script - tests network at increasing scales

set -e

echo "📈 Pangea Net Scale Testing"
echo "=========================="

# Function to run test at specific scale
run_scale_test() {
    local scale=$1
    echo "🔥 Testing at scale: $scale nodes"
    
    # Generate docker-compose for this scale
    cat > docker-compose.scale.yml << EOF
version: '3.8'
services:
EOF
    
    # Generate nodes
    for i in $(seq 1 $scale); do
        capnp_port=$((8079 + i))
        p2p_port=$((9089 + i))
        
        cat >> docker-compose.scale.yml << EOF
  node-$i:
    build: ./go
    hostname: node-$i
    ports:
      - "$capnp_port:8080"
      - "$p2p_port:9090"
    environment:
      - NODE_ID=$i
EOF
        
        if [ $i -eq 1 ]; then
            echo "    command: [\"./go-node\", \"-node-id=$i\", \"-capnp-addr=:8080\", \"-p2p-addr=:9090\"]" >> docker-compose.scale.yml
        else
            # Connect to previous nodes
            peers=""
            for j in $(seq 1 $((i-1))); do
                if [ -n "$peers" ]; then
                    peers="$peers,"
                fi
                peers="$peers$j:node-$j:9090"
            done
            echo "    command: [\"./go-node\", \"-node-id=$i\", \"-capnp-addr=:8080\", \"-p2p-addr=:9090\", \"-peers=$peers\"]" >> docker-compose.scale.yml
            echo "    depends_on: [node-1]" >> docker-compose.scale.yml
        fi
        
        echo "    networks: [pangea-net]" >> docker-compose.scale.yml
    done
    
    # Add AI for first node
    cat >> docker-compose.scale.yml << EOF
  ai-1:
    build: ./python
    hostname: ai-1
    command: ["python", "main.py", "predict", "--host", "node-1", "--port", "8080", "--poll-interval", "1.0"]
    depends_on: [node-1]
    networks: [pangea-net]

networks:
  pangea-net:
    driver: bridge
EOF
    
    # Start the network
    echo "🚀 Starting $scale-node network..."
    docker compose -f docker-compose.scale.yml up -d
    
    # Wait for startup
    echo "⏳ Waiting for network to stabilize..."
    sleep $((scale * 2 + 10))
    
    # Build node list for testing
    nodes=""
    for i in $(seq 1 $scale); do
        port=$((8079 + i))
        if [ -n "$nodes" ]; then
            nodes="$nodes localhost:$port"
        else
            nodes="localhost:$port"
        fi
    done
    
    # Run load test
    echo "🧪 Running load test on $scale nodes..."
    cd /home/abhinav/Desktop/WGT && python3 tools/load-testing/load_test.py --nodes $nodes --save "scale_test_${scale}nodes.json" --quick
    
    # Stop the network
    echo "🛑 Stopping $scale-node network..."
    docker compose -f docker-compose.scale.yml down
    
    # Clean up
    rm docker-compose.scale.yml
    
    echo "✅ Scale test complete for $scale nodes"
    echo ""
}

# Test at different scales
scales=(3 5 10 15 20)

for scale in "${scales[@]}"; do
    run_scale_test $scale
    sleep 5  # Brief pause between tests
done

echo "📊 Scale testing complete!"
echo "Results saved in scale_test_*nodes.json files"