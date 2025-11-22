"""
Command-line interface for easy execution of Python functions.
Provides simple commands for common operations.
"""
import click
import logging
import sys
import time
from pathlib import Path

# Add parent directory for relative imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.client.go_client import GoNodeClient
from src.ai.predictor import ThreatPredictor
from src.data.peer_health import PeerHealthManager
from src.utils.paths import get_go_schema_path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Pangea Net Python AI - Command Line Interface"""
    pass


@cli.command()
@click.option('--host', default='localhost', help='Go node host')
@click.option('--port', default=8080, help='Go node RPC port')
@click.option('--schema', default=None, help='Path to schema.capnp (default: auto-detect from project root)')
def connect(host, port, schema):
    """Connect to a Go node and test connection."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if client.connect():
        click.echo(f"✅ Connected to Go node at {host}:{port}")
        nodes = client.get_all_nodes()
        click.echo(f"Found {len(nodes)} nodes")
        client.disconnect()
    else:
        click.echo(f"❌ Failed to connect to {host}:{port}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--host', default='localhost', help='Go node host')
@click.option('--port', default=8080, help='Go node RPC port')
@click.option('--schema', default=None, help='Path to schema.capnp (default: auto-detect)')
def list_nodes(host, port, schema):
    """List all nodes from Go node."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect", err=True)
        sys.exit(1)
    
    nodes = client.get_all_nodes()
    click.echo(f"\nFound {len(nodes)} nodes:\n")
    for node in nodes:
        click.echo(f"  Node {node['id']}: latency={node['latencyMs']:.2f}ms, "
                  f"threat={node['threatScore']:.3f}, status={node['status']}")
    
    client.disconnect()


@cli.command()
@click.option('--host', default='localhost', help='Go node host')
@click.option('--port', default=8080, help='Go node RPC port')
@click.option('--schema', default=None, help='Path to schema.capnp (default: auto-detect)')
@click.argument('peer_id', type=int)
@click.argument('peer_host')
@click.argument('peer_port', type=int)
def connect_peer(host, port, schema, peer_id, peer_host, peer_port):
    """Connect to a new peer via Go node."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node", err=True)
        sys.exit(1)
    
    click.echo(f"Connecting to peer {peer_id} at {peer_host}:{peer_port}...")
    success, quality = client.connect_to_peer(peer_id, peer_host, peer_port)
    
    if success:
        click.echo(f"✅ Connected! Quality: latency={quality['latencyMs']:.2f}ms, "
                  f"jitter={quality['jitterMs']:.2f}ms")
    else:
        click.echo(f"❌ Connection failed", err=True)
    
    client.disconnect()


@cli.command()
@click.option('--host', default='localhost', help='Go node host')
@click.option('--port', default=8080, help='Go node RPC port')
@click.option('--schema', default=None, help='Path to schema.capnp (default: auto-detect)')
@click.argument('node_id', type=int)
@click.argument('threat_score', type=float)
def update_threat(host, port, schema, node_id, threat_score):
    """Update threat score for a node."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect", err=True)
        sys.exit(1)
    
    success = client.update_threat_score(node_id, threat_score)
    if success:
        click.echo(f"✅ Updated threat score for node {node_id} to {threat_score}")
    else:
        click.echo(f"❌ Failed to update", err=True)
    
    client.disconnect()


@cli.command()
@click.option('--host', default='localhost', help='Go node host')
@click.option('--port', default=8080, help='Go node RPC port')
@click.option('--schema', default=None, help='Path to schema.capnp (default: auto-detect)')
@click.option('--poll-interval', default=1.0, help='Polling interval in seconds')
@click.option('--window-size', default=100, help='Time series window size')
def predict(host, port, schema, poll_interval, window_size):
    """Start threat prediction loop."""
    click.echo("Starting threat predictor...")
    
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node", err=True)
        sys.exit(1)
    
    predictor = ThreatPredictor(
        client,
        window_size=window_size,
        poll_interval=poll_interval
    )
    
    try:
        predictor.start()
        click.echo("✅ Predictor running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
            # Show status
            healthy = predictor.get_healthy_peers()
            scores = predictor.get_peer_scores()
            click.echo(f"\rHealthy peers: {len(healthy)}, "
                      f"Total peers: {len(scores)}", nl=False)
    except KeyboardInterrupt:
        click.echo("\nStopping predictor...")
        predictor.stop()
        client.disconnect()
        click.echo("✅ Stopped")


@cli.command()
@click.option('--host', default='localhost', help='Go node host')
@click.option('--port', default=8080, help='Go node RPC port')
@click.option('--schema', default=None, help='Path to schema.capnp (default: auto-detect)')
def health_status(host, port, schema):
    """Show peer health status."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect", err=True)
        sys.exit(1)
    
    # Get connected peers
    peers = client.get_connected_peers()
    click.echo(f"\nConnected peers: {len(peers)}\n")
    
    for peer_id in peers:
        quality = client.get_connection_quality(peer_id)
        if quality:
            click.echo(f"  Peer {peer_id}:")
            click.echo(f"    Latency: {quality['latencyMs']:.2f}ms")
            click.echo(f"    Jitter: {quality['jitterMs']:.2f}ms")
            click.echo(f"    Packet Loss: {quality['packetLoss']*100:.2f}%")
    
    client.disconnect()


if __name__ == '__main__':
    import time
    cli()

