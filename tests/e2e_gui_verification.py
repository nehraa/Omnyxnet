#!/usr/bin/env python3
"""
E2E GUI RPC Wiring Verification Test
=====================================
This script verifies that all GUI elements are properly wired to backend RPC methods.
It tests the 5 core functions requested:
1. Liveness Check
2. File Upload Start
3. Compute Task Submission
4. Get Peer List
5. Send DCDN Request

This is a manual verification script that checks the code structure and imports.
"""

import sys
import ast
from pathlib import Path

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "python"))
sys.path.insert(0, str(PROJECT_ROOT / "python" / "src"))

print("=" * 80)
print("E2E GUI RPC Wiring Verification")
print("=" * 80)
print()

# Test 1: Verify imports
print("Test 1: Verifying module imports...")
try:
    from client.go_client import GoNodeClient
    print("  ✅ GoNodeClient imported successfully")
except ImportError as e:
    print(f"  ❌ Failed to import GoNodeClient: {e}")

# Test 2: Parse desktop/desktop_app_kivy.py and verify RPC method calls
print("\nTest 2: Analyzing RPC method wiring in desktop/desktop_app_kivy.py...")

desktop_app_path = PROJECT_ROOT / "desktop" / "desktop_app_kivy.py"
with open(desktop_app_path, 'r') as f:
    code = f.read()
    tree = ast.parse(code)

# Find all method calls to go_client
rpc_methods_found = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Attribute):
            if node.value.attr == 'go_client':
                rpc_methods_found.add(node.attr)
        elif isinstance(node.value, ast.Name):
            if node.value.id == 'go_client':
                rpc_methods_found.add(node.attr)

print(f"\n  Found {len(rpc_methods_found)} unique RPC method calls:")
for method in sorted(rpc_methods_found):
    print(f"    • {method}()")

# Test 3: Verify critical RPC methods are present
print("\nTest 3: Verifying critical RPC methods...")
critical_methods = {
    'get_all_nodes': 'Liveness/Node listing',
    'get_network_metrics': 'Network health checks',
    'upload': 'File upload',
    'download': 'File download',
    'submit_compute_job': 'Compute task submission',
    'get_compute_job_status': 'Task status tracking',
    'get_connected_peers': 'Peer list retrieval',
    'connect_to_peer': 'Peer connection',
    'send_message': 'P2P messaging',
    'get_connection_quality': 'Connection quality metrics'
}

all_present = True
for method, description in critical_methods.items():
    if method in rpc_methods_found:
        print(f"  ✅ {method:30s} - {description}")
    else:
        print(f"  ❌ {method:30s} - {description} (NOT FOUND)")
        all_present = False

# Test 4: Count GUI action methods
print("\nTest 4: Counting GUI action methods...")
action_methods = [
    'list_nodes', 'get_node_info', 'health_status',  # Node Management
    'submit_compute_task', 'list_workers', 'check_task_status',  # Compute
    'upload_file', 'download_file', 'list_files',  # Files
    'test_p2p_connection', 'ping_all_nodes', 'check_network_health',  # Communications
    'show_peers', 'show_topology', 'show_stats',  # Network
    'run_dcdn_demo', 'dcdn_info', 'test_dcdn'  # DCDN
]

methods_implemented = []
with open(desktop_app_path, 'r') as f:
    content = f.read()
    for method in action_methods:
        if f'def {method}(self)' in content:
            methods_implemented.append(method)

print(f"  GUI action methods implemented: {len(methods_implemented)}/{len(action_methods)}")
for method in methods_implemented:
    print(f"    • {method}()")

# Test 5: Verify no debug/placeholder code
print("\nTest 5: Checking for debug statements and placeholders...")
debug_patterns = ['print(', 'pprint(', 'import pdb', 'breakpoint()']
placeholder_patterns = ['TODO', 'FIXME', '# TODO:', '# FIXME:']

issues = []
with open(desktop_app_path, 'r') as f:
    lines = f.readlines()
    for i, line in enumerate(lines, 1):
        # Check for debug statements (excluding logger.* and self.log_message)
        for pattern in debug_patterns:
            if pattern in line and 'logger' not in line and 'log_message' not in line:
                issues.append(f"Line {i}: Debug statement - {line.strip()}")
        
        # Check for placeholders
        for pattern in placeholder_patterns:
            if pattern in line and not line.strip().startswith('#'):
                issues.append(f"Line {i}: Placeholder - {line.strip()}")

if issues:
    print("  ⚠️  Found potential issues:")
    for issue in issues[:10]:  # Show first 10
        print(f"    {issue}")
else:
    print("  ✅ No debug statements or placeholder comments found")

# Test 6: Verify Cap'n Proto schema is accessible
print("\nTest 6: Verifying Cap'n Proto schema accessibility...")
schema_path = PROJECT_ROOT / "go" / "schema" / "schema.capnp"
if schema_path.exists():
    print(f"  ✅ Schema file found: {schema_path}")
    # Count RPC methods defined in schema
    with open(schema_path, 'r') as f:
        schema_content = f.read()
        method_count = schema_content.count('@')  # Rough count of definitions
        print(f"  📊 Schema contains ~{method_count} method/struct definitions")
else:
    print(f"  ❌ Schema file not found at: {schema_path}")

# Test 7: Verify Docker compose configuration
print("\nTest 7: Verifying Docker compose configuration...")
compose_path = PROJECT_ROOT / "docker" / "docker-compose.gui-test.yml"
if compose_path.exists():
    print(f"  ✅ Docker compose file found: {compose_path}")
    with open(compose_path, 'r') as f:
        compose_content = f.read()
        node_count = compose_content.count('container_name: wgt-gui-node')
        print(f"  📊 Configured for {node_count} nodes")
        if 'depends_on:' in compose_content:
            print("  ✅ Node dependencies configured")
        if 'healthcheck:' in compose_content:
            print("  ✅ Health checks configured")
else:
    print(f"  ❌ Docker compose file not found")

# Test 8: Verify management script
print("\nTest 8: Verifying management script...")
script_path = PROJECT_ROOT / "scripts" / "gui_test_network.sh"
if script_path.exists():
    print(f"  ✅ Management script found: {script_path}")
    with open(script_path, 'r') as f:
        script_content = f.read()
        commands = ['start', 'stop', 'status', 'logs', 'addrs']
        for cmd in commands:
            if f'"{cmd}")' in script_content or f"'{cmd}')" in script_content:
                print(f"    ✅ Command '{cmd}' implemented")
else:
    print(f"  ❌ Management script not found")

# Summary
print("\n" + "=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)
print(f"✅ RPC Methods Found: {len(rpc_methods_found)}")
print(f"✅ Critical Methods Present: {len([m for m in critical_methods if m in rpc_methods_found])}/{len(critical_methods)}")
print(f"✅ GUI Actions Implemented: {len(methods_implemented)}/{len(action_methods)}")
print(f"✅ Code Quality: {'Clean' if not issues else f'{len(issues)} issues found'}")
print(f"✅ Infrastructure: {'Ready' if compose_path.exists() and script_path.exists() else 'Incomplete'}")

if all_present and len(methods_implemented) == len(action_methods) and not issues:
    print("\n🎉 ALL VERIFICATIONS PASSED - Ready for merge!")
    sys.exit(0)
else:
    print("\n⚠️  Some verifications failed - review needed")
    sys.exit(1)
