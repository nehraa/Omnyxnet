#!/bin/bash
# Quick containerization and testing script

set -e

echo "🐳 Pangea Net Containerization & Load Testing"
echo "============================================="

# Build images
echo "📦 Building Docker images..."
cd /home/abhinav/Desktop/WGT && docker compose -f deployment/compose/docker-compose.test.yml build

# Start the test network
echo "🚀 Starting test network (3 nodes + AI)..."
docker compose -f deployment/compose/docker-compose.test.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check health
echo "🔍 Checking service health..."
docker compose -f docker-compose.test.yml ps

# Run quick load test
echo "🧪 Running quick load test..."
cd /home/abhinav/Desktop/WGT && python3 tools/load-testing/load_test.py --nodes localhost:8080 localhost:8081 localhost:8082 --quick

# Show logs
echo "📋 Recent logs from nodes:"
echo "--- Node 1 ---"
docker compose -f ../../deployment/compose/docker-compose.test.yml logs --tail=5 node-1
echo "--- Node 2 ---"
docker compose -f ../../deployment/compose/docker-compose.test.yml logs --tail=5 node-2
echo "--- AI-1 ---"
docker compose -f ../../deployment/compose/docker-compose.test.yml logs --tail=5 ai-1

echo ""
echo "✅ Test network is running!"
echo "   Node 1: http://localhost:8080"
echo "   Node 2: http://localhost:8081"
echo "   Node 3: http://localhost:8082"
echo ""
echo "🧪 Run full load test:"
echo "   python3 load_test.py --save results.json"
echo ""
echo "🛑 Stop network:"
echo "   docker-compose -f docker-compose.test.yml down"