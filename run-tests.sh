#!/bin/bash
# Convenience script to run tests from project root

echo "🧪 Pangea Net - Test Suite Launcher"
echo "==================================="

# Check if we're in the right directory
if [ ! -d "tools/scripts" ]; then
    echo "❌ Error: Run this script from the project root directory"
    exit 1
fi

# Make scripts executable
chmod +x tools/scripts/*.sh

# Run the test suite
cd tools/scripts && ./test_suite.sh "$@"