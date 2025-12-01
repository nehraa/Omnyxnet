#!/bin/bash
# Convenience script to run tests from project root

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🧪 Pangea Net - Test Suite Launcher"
echo "==================================="

# Check if we're in the right directory
if [ ! -d "tools/scripts" ]; then
    echo "❌ Error: tools/scripts directory not found"
    exit 1
fi

# Make scripts executable
chmod +x tools/scripts/*.sh

# Run the test suite
cd tools/scripts && ./test_suite.sh "$@"