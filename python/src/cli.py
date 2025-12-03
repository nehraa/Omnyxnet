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
from src.utils.paths import get_go_schema_path

# Conditional AI imports - torch may not be installed
try:
    from src.ai.predictor import ThreatPredictor
    _AI_AVAILABLE = True
except ImportError:
    ThreatPredictor = None
    _AI_AVAILABLE = False

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
    if not _AI_AVAILABLE or ThreatPredictor is None:
        click.echo("❌ AI features not available. Install torch for full AI support:", err=True)
        click.echo("   pip install torch>=2.0.0", err=True)
        sys.exit(1)
    
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


# ============================================================================
# Streaming Commands (Uses Go networking per Golden Rule)
# ============================================================================

@cli.group()
def streaming():
    """
    Streaming commands for video/audio/chat.
    
    All networking is handled by Go. Python manages the high-level operations
    and captures/displays media. This follows the Golden Rule:
    - Rust: Files and memory operations
    - Go: All networking (UDP, TCP, QUIC)
    - Python: AI and high-level management
    """
    pass


@streaming.command()
@click.option('--host', default='localhost', help='Go node host')
@click.option('--port', default=8080, help='Go node RPC port')
@click.option('--stream-port', default=9996, type=int, help='Streaming port')
@click.option('--type', 'stream_type', type=click.Choice(['video', 'audio', 'chat']), 
              default='video', help='Stream type')
@click.option('--peer-host', default='', help='Peer host to connect to')
@click.option('--peer-port', default=9996, type=int, help='Peer streaming port')
@click.option('--schema', default=None, help='Path to schema.capnp')
def start(host, port, stream_port, stream_type, peer_host, peer_port, schema):
    """
    Start streaming service.
    
    This command starts Go's streaming service and connects to a peer.
    The actual network I/O is handled by Go, not Python.
    
    Example:
        # Start as server (waits for peer)
        python main.py streaming start --stream-port 9996
        
        # Start and connect to peer
        python main.py streaming start --peer-host 192.168.1.100 --peer-port 9996
    """
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node at {host}:{port}", err=True)
        sys.exit(1)
    
    type_map = {'video': 0, 'audio': 1, 'chat': 2}
    type_code = type_map[stream_type]
    
    click.echo(f"🎥 Starting {stream_type} streaming on port {stream_port}...")
    
    success = client.start_streaming(stream_port, peer_host, peer_port, type_code)
    if success:
        click.echo(f"✅ Streaming service started")
        if peer_host:
            click.echo(f"   Connected to {peer_host}:{peer_port}")
        else:
            click.echo(f"   Waiting for peer connections on port {stream_port}")
    else:
        click.echo(f"❌ Failed to start streaming", err=True)
        client.disconnect()
        sys.exit(1)
    
    client.disconnect()


@streaming.command()
@click.option('--host', default='localhost', help='Go node host')
@click.option('--port', default=8080, help='Go node RPC port')
@click.option('--schema', default=None, help='Path to schema.capnp')
def stop(host, port, schema):
    """Stop streaming service."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect", err=True)
        sys.exit(1)
    
    success = client.stop_streaming()
    if success:
        click.echo(f"✅ Streaming stopped")
    else:
        click.echo(f"❌ Failed to stop streaming", err=True)
    
    client.disconnect()


@streaming.command()
@click.option('--host', default='localhost', help='Go node host')
@click.option('--port', default=8080, help='Go node RPC port')
@click.option('--schema', default=None, help='Path to schema.capnp')
def stats(host, port, schema):
    """Show streaming statistics."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect", err=True)
        sys.exit(1)
    
    stream_stats = client.get_stream_stats()
    if stream_stats:
        click.echo("\n📊 Streaming Statistics:")
        click.echo(f"   Frames Sent:     {stream_stats.get('framesSent', 0)}")
        click.echo(f"   Frames Received: {stream_stats.get('framesReceived', 0)}")
        click.echo(f"   Bytes Sent:      {stream_stats.get('bytesSent', 0)}")
        click.echo(f"   Bytes Received:  {stream_stats.get('bytesReceived', 0)}")
        click.echo(f"   Avg Latency:     {stream_stats.get('avgLatencyMs', 0):.2f}ms")
    else:
        click.echo("No streaming statistics available")
    
    client.disconnect()


@streaming.command()
@click.option('--host', default='localhost', help='Go node host')
@click.option('--port', default=8080, help='Go node RPC port')
@click.argument('peer_host')
@click.argument('peer_port', type=int)
@click.option('--schema', default=None, help='Path to schema.capnp')
def connect_peer(host, port, peer_host, peer_port, schema):
    """Connect to a streaming peer."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect", err=True)
        sys.exit(1)
    
    success, peer_addr = client.connect_stream_peer(peer_host, peer_port)
    if success:
        click.echo(f"✅ Connected to streaming peer at {peer_addr}")
    else:
        click.echo(f"❌ Failed to connect to {peer_host}:{peer_port}", err=True)
    
    client.disconnect()


# ============================================================================
# AI Commands (Phase 2)
# ============================================================================

@cli.group()
def ai():
    """AI/ML commands for translation, lipsync, and federated learning."""
    pass


@ai.command()
@click.option('--source-lang', default='eng_Latn', help='Source language code')
@click.option('--target-lang', default='spa_Latn', help='Target language code')
@click.option('--gpu/--no-gpu', default=True, help='Use GPU if available')
def translate_test(source_lang, target_lang, gpu):
    """
    Test the translation pipeline (bypass mode).
    
    This tests the AI translation wiring without actual model inference.
    Models are loaded in placeholder mode for testing.
    """
    try:
        from src.ai.translation_pipeline import TranslationPipeline, TranslationConfig
        
        config = TranslationConfig(
            source_lang=source_lang,
            target_lang=target_lang,
            use_gpu=gpu
        )
        
        pipeline = TranslationPipeline(config)
        click.echo("✅ Translation pipeline initialized (placeholder mode)")
        click.echo(f"   Source: {source_lang}")
        click.echo(f"   Target: {target_lang}")
        click.echo(f"   GPU: {'enabled' if gpu else 'disabled'}")
        
        # Get latency stats
        stats = pipeline.get_latency_stats()
        click.echo(f"   Target latency: {stats['target_latency_ms']}ms")
        
    except ImportError as e:
        click.echo(f"⚠️  Translation pipeline not fully available: {e}")
        click.echo("   This is expected if torch is not installed (minimal mode)")


@ai.command()
def lipsync_test():
    """
    Test the video lipsync pipeline (bypass mode).
    
    This tests the AI lipsync wiring without actual model inference.
    """
    try:
        from src.ai.video_lipsync import VideoLipsync, LipsyncConfig
        
        config = LipsyncConfig()
        lipsync = VideoLipsync(config)
        click.echo("✅ Video lipsync module initialized (placeholder mode)")
        
        stats = lipsync.get_latency_stats()
        click.echo(f"   Target latency: {stats.get('target_latency_ms', 'N/A')}ms")
        
    except ImportError as e:
        click.echo(f"⚠️  Lipsync module not fully available: {e}")


@ai.command()
def federated_test():
    """
    Test the federated learning pipeline (bypass mode).
    
    This tests the P2P-FL wiring without actual training.
    """
    try:
        from src.ai.federated_learning import P2PFederatedLearning, FederatedConfig
        
        config = FederatedConfig()
        fl = P2PFederatedLearning(config)
        click.echo("✅ Federated learning module initialized")
        
        # Get model size
        model_size = fl.get_model_size()
        click.echo(f"   Model size: {model_size / 1024:.2f}KB")
        
        stats = fl.get_statistics()
        click.echo(f"   Rounds completed: {stats.get('rounds_completed', 0)}")
        
    except ImportError as e:
        click.echo(f"⚠️  Federated learning not fully available: {e}")


# ============================================================================
# Chat Commands (P2P Communication)
# ============================================================================

@cli.group()
def chat():
    """
    P2P Chat commands.
    
    Chat functionality is handled by Go's communication service using libp2p.
    Python provides high-level commands while Go handles all networking.
    
    Usage:
        python main.py chat send <peer_id> "Hello!"
        python main.py chat history
    """
    pass


@chat.command()
@click.option('--host', default='localhost', help='Go node host')
@click.option('--port', default=8080, help='Go node RPC port')
@click.option('--schema', default=None, help='Path to schema.capnp')
@click.argument('peer_id')
@click.argument('message')
def send(host, port, schema, peer_id, message):
    """
    Send a chat message to a peer.
    
    The message is sent via Go's P2P communication service using libp2p streams.
    Chat history is automatically saved by the Go service.
    
    Example:
        python main.py chat send 12D3KooW... "Hello, peer!"
    """
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node at {host}:{port}", err=True)
        sys.exit(1)
    
    click.echo(f"💬 Sending message to {peer_id[:12]}...")
    
    # Send chat message via RPC
    success = client.send_chat_message(peer_id, message)
    if success:
        click.echo(f"✅ Message sent!")
    else:
        click.echo(f"❌ Failed to send message", err=True)
    
    client.disconnect()


@chat.command()
@click.option('--host', default='localhost', help='Go node host')
@click.option('--port', default=8080, help='Go node RPC port')
@click.option('--peer', default=None, help='Filter by peer ID')
@click.option('--limit', default=20, help='Maximum messages to show')
@click.option('--schema', default=None, help='Path to schema.capnp')
def history(host, port, peer, limit, schema):
    """
    View chat history.
    
    Shows recent chat messages from all peers or a specific peer.
    Chat history is stored by Go's communication service.
    
    Example:
        python main.py chat history
        python main.py chat history --peer 12D3KooW...
        python main.py chat history --limit 50
    """
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node at {host}:{port}", err=True)
        sys.exit(1)
    
    click.echo(f"\n💬 Chat History")
    click.echo("=" * 60)
    
    # Get chat history via RPC
    messages = client.get_chat_history(peer)
    
    if not messages:
        click.echo("No messages found.")
    else:
        # Show last N messages
        for msg in messages[-limit:]:
            from_id = msg.get('from', 'Unknown')[:12]
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            click.echo(f"[{timestamp}] {from_id}: {content}")
    
    click.echo("")
    client.disconnect()


@chat.command()
@click.option('--host', default='localhost', help='Go node host')
@click.option('--port', default=8080, help='Go node RPC port')
@click.option('--schema', default=None, help='Path to schema.capnp')
def peers(host, port, schema):
    """
    List peers with active chat connections.
    
    Shows peers that have active chat streams via libp2p.
    """
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node at {host}:{port}", err=True)
        sys.exit(1)
    
    click.echo(f"\n💬 Active Chat Peers")
    click.echo("=" * 60)
    
    # Get connected peers via RPC
    peers_list = client.get_connected_peers()
    
    if not peers_list:
        click.echo("No active chat peers.")
    else:
        for i, peer_id in enumerate(peers_list, 1):
            click.echo(f"  {i}. {peer_id[:16]}...")
    
    click.echo("")
    client.disconnect()


# ============================================================================
# Voice Commands (P2P Communication)
# ============================================================================

@cli.group()
def voice():
    """
    P2P Voice commands.
    
    Voice functionality is handled by Go's communication service using libp2p.
    Python provides high-level commands while Go handles all networking.
    
    Usage:
        python main.py voice start
        python main.py voice stop
    """
    pass


@voice.command()
@click.option('--host', default='localhost', help='Go node host')
@click.option('--port', default=8080, help='Go node RPC port')
@click.option('--peer-host', default='', help='Peer host to connect to')
@click.option('--peer-port', default=0, type=int, help='Peer port')
@click.option('--schema', default=None, help='Path to schema.capnp')
def start(host, port, peer_host, peer_port, schema):
    """
    Start voice streaming.
    
    Starts the Go voice streaming service using libp2p.
    If peer-host is provided, connects to that peer.
    Otherwise, waits for incoming connections.
    """
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node at {host}:{port}", err=True)
        sys.exit(1)
    
    click.echo("🎤 Starting voice streaming...")
    
    success = client.start_streaming(0, peer_host, peer_port, 1)  # 1 = audio
    if success:
        click.echo("✅ Voice streaming started")
        if peer_host:
            click.echo(f"   Connected to {peer_host}:{peer_port}")
        else:
            click.echo("   Waiting for peer connections...")
    else:
        click.echo("❌ Failed to start voice streaming", err=True)
    
    client.disconnect()


@voice.command()
@click.option('--host', default='localhost', help='Go node host')
@click.option('--port', default=8080, help='Go node RPC port')
@click.option('--schema', default=None, help='Path to schema.capnp')
def stop(host, port, schema):
    """Stop voice streaming."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect", err=True)
        sys.exit(1)
    
    success = client.stop_streaming()
    if success:
        click.echo("✅ Voice streaming stopped")
    else:
        click.echo("❌ Failed to stop voice streaming", err=True)
    
    client.disconnect()


# ============================================================================
# Video Commands (P2P Communication)
# ============================================================================

@cli.group()
def video():
    """
    P2P Video commands.
    
    Video functionality is handled by Go's communication service using libp2p.
    Python provides high-level commands while Go handles all networking.
    
    Usage:
        python main.py video start
        python main.py video stop
    """
    pass


@video.command()
@click.option('--host', default='localhost', help='Go node host')
@click.option('--port', default=8080, help='Go node RPC port')
@click.option('--peer-host', default='', help='Peer host to connect to')
@click.option('--peer-port', default=0, type=int, help='Peer port')
@click.option('--schema', default=None, help='Path to schema.capnp')
def start(host, port, peer_host, peer_port, schema):
    """
    Start video streaming.
    
    Starts the Go video streaming service using libp2p.
    If peer-host is provided, connects to that peer.
    Otherwise, waits for incoming connections.
    """
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node at {host}:{port}", err=True)
        sys.exit(1)
    
    click.echo("🎥 Starting video streaming...")
    
    success = client.start_streaming(0, peer_host, peer_port, 0)  # 0 = video
    if success:
        click.echo("✅ Video streaming started")
        if peer_host:
            click.echo(f"   Connected to {peer_host}:{peer_port}")
        else:
            click.echo("   Waiting for peer connections...")
    else:
        click.echo("❌ Failed to start video streaming", err=True)
    
    client.disconnect()


@video.command()
@click.option('--host', default='localhost', help='Go node host')
@click.option('--port', default=8080, help='Go node RPC port')
@click.option('--schema', default=None, help='Path to schema.capnp')
def stop(host, port, schema):
    """Stop video streaming."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect", err=True)
        sys.exit(1)
    
    success = client.stop_streaming()
    if success:
        click.echo("✅ Video streaming stopped")
    else:
        click.echo("❌ Failed to stop video streaming", err=True)
    
    client.disconnect()


if __name__ == '__main__':
    import time
    cli()

