"""
Command-line interface for easy execution of Python functions.
Provides simple commands for common operations.
"""

import click
import logging
import subprocess  # Used by DCDN commands to call Rust implementation
import sys
import time
from pathlib import Path

# Add parent directory for relative imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.client.go_client import GoNodeClient
from src.utils.paths import get_go_schema_path

from typing import Any, Optional

# Conditional AI imports - torch may not be installed
ThreatPredictor: Optional[Any] = None
try:
    from src.ai.predictor import ThreatPredictor as _ThreatPredictor

    ThreatPredictor = _ThreatPredictor
    _AI_AVAILABLE = True
except ImportError:
    _AI_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# Stream Type Constants (for clarity in RPC calls)
# These match the Go service's expected values
# ============================================================================
STREAM_TYPE_VIDEO = 0  # Video streaming
STREAM_TYPE_AUDIO = 1  # Audio/voice streaming
STREAM_TYPE_CHAT = 2  # Chat messaging


@click.group()
def cli():
    """Pangea Net Python AI - Command Line Interface"""
    pass


@cli.command(name="connect-peer")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option(
    "--schema",
    default=None,
    help="Path to schema.capnp (default: auto-detect from project root)",
)
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
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option(
    "--schema", default=None, help="Path to schema.capnp (default: auto-detect)"
)
def list_nodes(host, port, schema):
    """List all nodes from Go node."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo("❌ Failed to connect", err=True)
        sys.exit(1)

    nodes = client.get_all_nodes()
    click.echo(f"\nFound {len(nodes)} nodes:\n")
    for node in nodes:
        click.echo(
            f"  Node {node['id']}: latency={node['latencyMs']:.2f}ms, "
            f"threat={node['threatScore']:.3f}, status={node['status']}"
        )

    client.disconnect()


@cli.command()
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option(
    "--schema", default=None, help="Path to schema.capnp (default: auto-detect)"
)
@click.argument("peer_id", type=int)
@click.argument("peer_host")
@click.argument("peer_port", type=int)
def connect_peer_node(host, port, schema, peer_id, peer_host, peer_port):
    """Connect to a new peer via Go node."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo("❌ Failed to connect to Go node", err=True)
        sys.exit(1)

    click.echo(f"Connecting to peer {peer_id} at {peer_host}:{peer_port}...")
    success, quality = client.connect_to_peer(peer_id, peer_host, peer_port)

    if success:
        click.echo(
            f"✅ Connected! Quality: latency={quality['latencyMs']:.2f}ms, "
            f"jitter={quality['jitterMs']:.2f}ms"
        )
    else:
        click.echo("❌ Connection failed", err=True)

    client.disconnect()


@cli.command()
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option(
    "--schema", default=None, help="Path to schema.capnp (default: auto-detect)"
)
@click.argument("node_id", type=int)
@click.argument("threat_score", type=float)
def update_threat(host, port, schema, node_id, threat_score):
    """Update threat score for a node."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo("❌ Failed to connect", err=True)
        sys.exit(1)

    success = client.update_threat_score(node_id, threat_score)
    if success:
        click.echo(f"✅ Updated threat score for node {node_id} to {threat_score}")
    else:
        click.echo("❌ Failed to update", err=True)

    client.disconnect()


@cli.command()
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option(
    "--schema", default=None, help="Path to schema.capnp (default: auto-detect)"
)
@click.option("--poll-interval", default=1.0, help="Polling interval in seconds")
@click.option("--window-size", default=100, help="Time series window size")
def predict(host, port, schema, poll_interval, window_size):
    """Start threat prediction loop."""
    if not _AI_AVAILABLE or ThreatPredictor is None:
        click.echo(
            "❌ AI features not available. Install torch for full AI support:", err=True
        )
        click.echo("   pip install torch>=2.0.0", err=True)
        sys.exit(1)

    click.echo("Starting threat predictor...")

    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo("❌ Failed to connect to Go node", err=True)
        sys.exit(1)

    predictor = ThreatPredictor(
        client, window_size=window_size, poll_interval=poll_interval
    )

    try:
        predictor.start()
        click.echo("✅ Predictor running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
            # Show status
            healthy = predictor.get_healthy_peers()
            scores = predictor.get_peer_scores()
            click.echo(
                f"\rHealthy peers: {len(healthy)}, " f"Total peers: {len(scores)}",
                nl=False,
            )
    except KeyboardInterrupt:
        click.echo("\nStopping predictor...")
        predictor.stop()
        client.disconnect()
        click.echo("✅ Stopped")


@cli.command()
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option(
    "--schema", default=None, help="Path to schema.capnp (default: auto-detect)"
)
def health_status(host, port, schema):
    """Show peer health status."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo("❌ Failed to connect", err=True)
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


@streaming.command(name="start")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--stream-port", default=9996, type=int, help="Streaming port")
@click.option(
    "--type",
    "stream_type",
    type=click.Choice(["video", "audio", "chat"]),
    default="video",
    help="Stream type",
)
@click.option("--peer-host", default="", help="Peer host to connect to")
@click.option("--peer-port", default=9996, type=int, help="Peer streaming port")
@click.option("--schema", default=None, help="Path to schema.capnp")
def streaming_start(host, port, stream_port, stream_type, peer_host, peer_port, schema):
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

    type_map = {"video": 0, "audio": 1, "chat": 2}
    type_code = type_map[stream_type]

    click.echo(f"🎥 Starting {stream_type} streaming on port {stream_port}...")

    success = client.start_streaming(stream_port, peer_host, peer_port, type_code)
    if success:
        click.echo("✅ Streaming service started")
        if peer_host:
            click.echo(f"   Connected to {peer_host}:{peer_port}")
        else:
            click.echo(f"   Waiting for peer connections on port {stream_port}")
    else:
        click.echo("❌ Failed to start streaming", err=True)
        client.disconnect()
        sys.exit(1)

    client.disconnect()


@streaming.command(name="stop")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--schema", default=None, help="Path to schema.capnp")
def streaming_stop(host, port, schema):
    """Stop streaming service."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo("❌ Failed to connect", err=True)
        sys.exit(1)

    success = client.stop_streaming()
    if success:
        click.echo("✅ Streaming stopped")
    else:
        click.echo("❌ Failed to stop streaming", err=True)

    client.disconnect()


@streaming.command(name="stats")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--schema", default=None, help="Path to schema.capnp")
def streaming_stats(host, port, schema):
    """Show streaming statistics."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo("❌ Failed to connect", err=True)
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


@streaming.command(name="connect-peer")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.argument("peer_host")
@click.argument("peer_port", type=int)
@click.option("--schema", default=None, help="Path to schema.capnp")
def streaming_connect_peer(host, port, peer_host, peer_port, schema):
    """Connect to a streaming peer."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo("❌ Failed to connect", err=True)
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
@click.option("--source-lang", default="eng_Latn", help="Source language code")
@click.option("--target-lang", default="spa_Latn", help="Target language code")
@click.option("--gpu/--no-gpu", default=True, help="Use GPU if available")
def translate_test(source_lang, target_lang, gpu):
    """
    Test the translation pipeline (bypass mode).

    This tests the AI translation wiring without actual model inference.
    Models are loaded in placeholder mode for testing.
    """
    try:
        from src.ai.translation_pipeline import TranslationPipeline, TranslationConfig

        config = TranslationConfig(
            source_lang=source_lang, target_lang=target_lang, use_gpu=gpu
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
        python main.py chat peers
    """
    pass


@chat.command()
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--schema", default=None, help="Path to schema.capnp")
@click.argument("peer_id")
@click.argument("message")
def chat_send(host, port, schema, peer_id, message):
    """
    Send a chat message to a peer.

    The message is sent via Go's P2P communication service using libp2p streams.
    Chat history is automatically saved by the Go service.

    Example:
        python main.py chat send 12D3KooW... "Hello, peer!"

    Note: Full chat functionality requires the Go communication service RPC methods
    to be implemented. Currently uses the existing sendChatMessage RPC.

    Args:
        peer_id: The libp2p peer ID or address to send the message to.
                 The Go service handles mapping peer IDs to addresses if needed.
        message: The text message to send.
    """
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node at {host}:{port}", err=True)
        sys.exit(1)

    click.echo(
        f"💬 Sending message to {peer_id[:12] if len(peer_id) > 12 else peer_id}..."
    )

    # Send chat message via RPC
    # Note: peer_id is passed to send_chat_message; the Go service handles
    # mapping peer IDs to addresses if needed
    success = client.send_chat_message(peer_id, message)
    if success:
        click.echo("✅ Message sent!")
    else:
        click.echo("❌ Failed to send message", err=True)

    client.disconnect()


@chat.command()
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--peer", default=None, help="Filter by peer ID")
@click.option("--limit", default=20, help="Maximum messages to show")
@click.option("--schema", default=None, help="Path to schema.capnp")
def history(host, port, peer, limit, schema):
    """
    View chat history.

    Shows recent chat messages from all peers or a specific peer.
    Chat history is stored by Go's communication service at:
    ~/.pangea/communication/chat_history.json

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

    click.echo("\n💬 Chat History")
    click.echo("=" * 60)

    # Get chat history via RPC or local file
    messages = client.get_chat_history(peer)

    if not messages:
        click.echo("No messages found.")
        click.echo(
            "\nNote: Chat history is stored at ~/.pangea/communication/chat_history.json"
        )
    else:
        # Show last N messages
        for msg in messages[-limit:]:
            from_id = msg.get("from", "Unknown")[:12]
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            click.echo(f"[{timestamp}] {from_id}: {content}")

    click.echo("")
    client.disconnect()


@chat.command()
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--schema", default=None, help="Path to schema.capnp")
def peers(host, port, schema):
    """
    List peers with active chat connections.

    Shows peers that have active connections via libp2p.

    Note: Returns node IDs from the Go node. The RPC currently returns
    integer node IDs; future versions will return full libp2p peer IDs
    when the communication service RPC is fully integrated.
    """
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node at {host}:{port}", err=True)
        sys.exit(1)

    click.echo("\n💬 Connected Peers")
    click.echo("=" * 60)

    # Get connected peers via RPC (returns node IDs as integers)
    peers_list = client.get_connected_peers()

    if not peers_list:
        click.echo("No connected peers.")
    else:
        for i, peer_id in enumerate(peers_list, 1):
            # Handle both int (node ID) and string (libp2p peer ID) types
            # The current RPC returns node IDs as integers, but future versions
            # may return libp2p peer ID strings
            if isinstance(peer_id, int):
                click.echo(f"  {i}. Node {peer_id}")
            else:
                peer_str = str(peer_id)
                click.echo(f"  {i}. {peer_str[:16]}...")

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
        python main.py voice stats
    """
    pass


@voice.command(name="start")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--peer-host", default="", help="Peer host to connect to")
@click.option("--peer-port", default=0, type=int, help="Peer port")
@click.option("--schema", default=None, help="Path to schema.capnp")
def voice_start(host, port, peer_host, peer_port, schema):
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

    # Start streaming with STREAM_TYPE_AUDIO
    # Parameters: (stream_port=0 for auto, peer_host, peer_port, stream_type=AUDIO)
    success = client.start_streaming(0, peer_host, peer_port, STREAM_TYPE_AUDIO)
    if success:
        click.echo("✅ Voice streaming started")
        if peer_host:
            click.echo(f"   Connected to {peer_host}:{peer_port}")
        else:
            click.echo("   Waiting for peer connections...")
    else:
        click.echo("❌ Failed to start voice streaming", err=True)

    client.disconnect()


@voice.command(name="stop")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--schema", default=None, help="Path to schema.capnp")
def voice_stop(host, port, schema):
    """Stop voice streaming."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo("❌ Failed to connect", err=True)
        sys.exit(1)

    success = client.stop_streaming()
    if success:
        click.echo("✅ Voice streaming stopped")
    else:
        click.echo("❌ Failed to stop voice streaming", err=True)

    client.disconnect()


@voice.command(name="stats")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--schema", default=None, help="Path to schema.capnp")
def voice_stats(host, port, schema):
    """Show voice streaming statistics."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo("❌ Failed to connect", err=True)
        sys.exit(1)

    stream_stats = client.get_stream_stats()
    if stream_stats:
        click.echo("\n🎤 Voice Streaming Statistics:")
        click.echo(f"   Bytes Sent:      {stream_stats.get('bytesSent', 0)}")
        click.echo(f"   Bytes Received:  {stream_stats.get('bytesReceived', 0)}")
        click.echo(f"   Avg Latency:     {stream_stats.get('avgLatencyMs', 0):.2f}ms")
    else:
        click.echo("No voice streaming statistics available")

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
        python main.py video stats
    """
    pass


@video.command(name="start")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--peer-host", default="", help="Peer host to connect to")
@click.option("--peer-port", default=0, type=int, help="Peer port")
@click.option("--schema", default=None, help="Path to schema.capnp")
def video_start(host, port, peer_host, peer_port, schema):
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

    # Start streaming with STREAM_TYPE_VIDEO
    # Parameters: (stream_port=0 for auto, peer_host, peer_port, stream_type=VIDEO)
    success = client.start_streaming(0, peer_host, peer_port, STREAM_TYPE_VIDEO)
    if success:
        click.echo("✅ Video streaming started")
        if peer_host:
            click.echo(f"   Connected to {peer_host}:{peer_port}")
        else:
            click.echo("   Waiting for peer connections...")
    else:
        click.echo("❌ Failed to start video streaming", err=True)

    client.disconnect()


@video.command(name="stop")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--schema", default=None, help="Path to schema.capnp")
def video_stop(host, port, schema):
    """Stop video streaming."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo("❌ Failed to connect", err=True)
        sys.exit(1)

    success = client.stop_streaming()
    if success:
        click.echo("✅ Video streaming stopped")
    else:
        click.echo("❌ Failed to stop video streaming", err=True)

    client.disconnect()


@video.command(name="stats")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--schema", default=None, help="Path to schema.capnp")
def video_stats(host, port, schema):
    """Show video streaming statistics."""
    schema_path = schema or get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)
    if not client.connect():
        click.echo("❌ Failed to connect", err=True)
        sys.exit(1)

    stream_stats = client.get_stream_stats()
    if stream_stats:
        click.echo("\n🎥 Video Streaming Statistics:")
        click.echo(f"   Frames Sent:     {stream_stats.get('framesSent', 0)}")
        click.echo(f"   Frames Received: {stream_stats.get('framesReceived', 0)}")
        click.echo(f"   Bytes Sent:      {stream_stats.get('bytesSent', 0)}")
        click.echo(f"   Bytes Received:  {stream_stats.get('bytesReceived', 0)}")
        click.echo(f"   Avg Latency:     {stream_stats.get('avgLatencyMs', 0):.2f}ms")
    else:
        click.echo("No video streaming statistics available")

    client.disconnect()


# ============================================================================
# Compute Commands (Distributed Compute System)
# ============================================================================


@cli.group()
def compute():
    """
    Distributed Compute commands.

    The Distributed Compute System allows running parallel computations
    across multiple nodes in the network. Following the Golden Rule:
    - Rust: Compute sandbox (WASM), verification, split/merge
    - Go: Orchestration, load balancing, task delegation
    - Python: Job definition, data preprocessing, result visualization

    Usage:
        python main.py compute submit --input data.bin
        python main.py compute status <job_id>
        python main.py compute result <job_id>
    """
    pass


@compute.command()
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option(
    "--input", "input_file", type=click.Path(exists=True), help="Input data file"
)
@click.option("--input-text", default=None, help="Input text data")
@click.option("--timeout", default=300, help="Job timeout in seconds")
@click.option("--priority", default=5, help="Job priority (1-10)")
@click.option("--schema", default=None, help="Path to schema.capnp")
def submit(host, port, input_file, input_text, timeout, priority, schema):
    """
    Submit a compute job.

    Submits a job to the distributed compute network. The job will be
    split, distributed across workers, and results merged automatically.

    Example:
        python main.py compute submit --input large_data.bin
        python main.py compute submit --input-text "Hello, World!"
    """
    from src.compute import Job, ComputeClient

    # Get input data
    if input_file:
        with open(input_file, "rb") as f:
            input_data = f.read()
        click.echo(f"📁 Read {len(input_data)} bytes from {input_file}")
    elif input_text:
        input_data = input_text.encode("utf-8")
    else:
        click.echo(
            "❌ Error: No input provided. Use --input FILE or --input-text TEXT to specify input data.",
            err=True,
        )
        sys.exit(1)

    # Create a simple identity job for demonstration
    @Job.define
    def identity_job():
        @Job.split
        def split(data):
            chunk_size = max(1024, len(data) // 8)
            return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

        @Job.execute
        def execute(chunk):
            return chunk  # Identity

        @Job.merge
        def merge(results):
            return b"".join(results)

    client = ComputeClient(host, port)
    if not client.connect():
        click.echo(f"❌ Failed to connect to {host}:{port}", err=True)
        sys.exit(1)

    try:
        click.echo(f"🚀 Submitting job with {len(input_data)} bytes...")
        job_id = client.submit_job(
            identity_job,
            input_data,
            timeout_secs=timeout,
            priority=priority,
        )
        click.echo(f"✅ Job submitted: {job_id}")

        # Wait for result
        click.echo("⏳ Waiting for result...")
        result, worker_node = client.get_result(job_id, timeout=timeout)
        click.echo(f"✅ Job completed! Result size: {len(result)} bytes")
        if worker_node and worker_node != "local":
            click.echo(f"   Executed by worker: {worker_node}")

        # Show preview
        if len(result) < 200:
            try:
                click.echo(f"   Result: {result.decode('utf-8')}")
            except UnicodeDecodeError:
                click.echo(f"   Result (hex): {result[:100].hex()}")

    except Exception as e:
        click.echo(f"❌ Job failed: {e}", err=True)
    finally:
        client.disconnect()


@compute.command()
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.argument("job_id")
def status(host, port, job_id):
    """
    Get status of a compute job.

    Shows the current status, progress, and other details of a running
    or completed job.
    """
    from src.compute import ComputeClient

    client = ComputeClient(host, port)
    if not client.connect():
        click.echo(f"❌ Failed to connect to {host}:{port}", err=True)
        sys.exit(1)

    try:
        status = client.get_status(job_id)
        click.echo(f"\n📊 Job Status: {job_id}")
        click.echo("=" * 50)
        click.echo(f"Status:           {status.status.name}")
        click.echo(f"Progress:         {status.progress * 100:.1f}%")
        click.echo(f"Completed Chunks: {status.completed_chunks}/{status.total_chunks}")
        if status.estimated_time_remaining > 0:
            click.echo(f"Est. Time Left:   {status.estimated_time_remaining}s")
        if status.error:
            click.echo(f"Error:            {status.error}")
    except KeyError:
        click.echo(f"❌ Job {job_id} not found", err=True)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
    finally:
        client.disconnect()


@compute.command()
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--output", "-o", type=click.Path(), help="Output file")
@click.argument("job_id")
def result(host, port, output, job_id):
    """
    Get result of a compute job.

    Retrieves the result of a completed job. Can save to file with --output.
    """
    from src.compute import ComputeClient

    client = ComputeClient(host, port)
    if not client.connect():
        click.echo(f"❌ Failed to connect to {host}:{port}", err=True)
        sys.exit(1)

    try:
        result, worker_node = client.get_result(job_id, timeout=10)

        if output:
            with open(output, "wb") as f:
                f.write(result)
            click.echo(f"✅ Result saved to {output} ({len(result)} bytes)")
        else:
            click.echo(f"\n📦 Job Result: {job_id}")
            click.echo("=" * 50)
            click.echo(f"Size: {len(result)} bytes")

            # Show preview
            preview = result[:500]
            try:
                text = preview.decode("utf-8")
                click.echo(f"Preview:\n{text}")
                if len(result) > 500:
                    click.echo(f"... ({len(result) - 500} more bytes)")
            except UnicodeDecodeError:
                click.echo(f"Preview (hex): {preview.hex()[:100]}")
                if len(result) > 500:
                    click.echo(f"... ({len(result) - 500} more bytes)")

    except KeyError:
        click.echo(f"❌ Job {job_id} not found", err=True)
    except TimeoutError:
        click.echo(f"❌ Job {job_id} not yet complete", err=True)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
    finally:
        client.disconnect()


@compute.command()
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.argument("job_id")
def cancel(host, port, job_id):
    """
    Cancel a running compute job.
    """
    from src.compute import ComputeClient

    client = ComputeClient(host, port)
    if not client.connect():
        click.echo(f"❌ Failed to connect to {host}:{port}", err=True)
        sys.exit(1)

    try:
        if client.cancel_job(job_id):
            click.echo(f"✅ Job {job_id} cancelled")
        else:
            click.echo(f"❌ Job {job_id} not found", err=True)
    finally:
        client.disconnect()


@compute.command()
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
def capacity(host, port):
    """
    Show compute capacity of the connected node.
    """
    from src.compute import ComputeClient

    client = ComputeClient(host, port)
    if not client.connect():
        click.echo(f"❌ Failed to connect to {host}:{port}", err=True)
        sys.exit(1)

    try:
        cap = client.get_capacity()
        click.echo("\n🖥️  Compute Capacity")
        click.echo("=" * 50)
        click.echo(f"CPU Cores:      {cap.cpu_cores}")
        click.echo(f"RAM:            {cap.ram_mb} MB")
        click.echo(f"Current Load:   {cap.current_load * 100:.1f}%")
        click.echo(f"Disk Space:     {cap.disk_mb} MB")
        click.echo(f"Bandwidth:      {cap.bandwidth_mbps} Mbps")
    finally:
        client.disconnect()


@compute.command("matrix-multiply")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option(
    "--size", "-s", default=10, type=int, help="Matrix size for generation (NxN)"
)
@click.option(
    "--file-a",
    "-a",
    type=click.Path(exists=True),
    help="Path to matrix A file (JSON, CSV, or .npy)",
)
@click.option(
    "--file-b",
    "-b",
    type=click.Path(exists=True),
    help="Path to matrix B file (optional, uses transpose of A if not provided)",
)
@click.option(
    "--output", "-o", type=click.Path(), help="Output file path to save result"
)
@click.option(
    "--generate",
    "-g",
    is_flag=True,
    help="Generate random matrices instead of using files",
)
@click.option(
    "--verify", "-v", is_flag=True, help="Verify result with NumPy (requires numpy)"
)
@click.option(
    "--connect",
    "-c",
    is_flag=True,
    help="Connect to remote node for distributed execution",
)
@click.option(
    "--peer-address",
    default=None,
    help="Manual peer multiaddr for mDNS bypass (e.g., /ip4/X.X.X.X/tcp/YYYY/p2p/QmID)",
)
def matrix_multiply(
    host, port, size, file_a, file_b, output, generate, verify, connect, peer_address
):
    """
    Perform distributed matrix multiplication.
    
    This command multiplies two matrices either locally or across the distributed
    compute network. Supports random generation, file input, and NumPy verification.
    
    \b
    Examples:
        # Generate and multiply random 10x10 matrices locally
        pangea compute matrix-multiply --size 10 --generate
        
        # Generate and multiply 100x100 matrices with verification
        pangea compute matrix-multiply --size 100 --generate --verify
        
        # Use file input
        pangea compute matrix-multiply --file-a matrix_a.json --file-b matrix_b.json
        
        # Distributed execution with auto peer discovery
        pangea compute matrix-multiply --size 50 --generate --connect
        
        # Distributed with manual peer address (bypass mDNS)
        pangea compute matrix-multiply --size 50 --generate --connect \\
            --peer-address /ip4/192.168.1.100/tcp/9081/p2p/QmXYZ...
        
        # Save result to file
        pangea compute matrix-multiply --size 20 --generate --output result.json
    """
    import time
    from src.compute import Job, ComputeClient
    from src.matrix_utils import (
        serialize_matrix,
        deserialize_matrix,
        matrix_multiply_block,
        generate_random_matrix,
        add_matrices,
        matrix_to_string,
        load_matrix_file,
        save_matrix_file,
        verify_with_numpy,
        has_numpy,
    )
    import struct
    from typing import List

    click.echo("=" * 60)
    click.echo("🧮 DISTRIBUTED MATRIX MULTIPLICATION")
    click.echo("=" * 60)

    # Get input matrices
    if generate:
        click.echo(f"\n🎲 Generating {size}x{size} random matrices...")
        matrix_a = generate_random_matrix(size, size, seed=42)
        matrix_b = generate_random_matrix(size, size, seed=43)
        click.echo(f"   Matrix A: {size}x{size}")
        click.echo(f"   Matrix B: {size}x{size}")
    elif file_a:
        click.echo(f"\n📂 Loading matrix A from: {file_a}")
        matrix_a = load_matrix_file(file_a)
        a_rows, a_cols = len(matrix_a), len(matrix_a[0])
        click.echo(f"   Dimensions: {a_rows}x{a_cols}")

        if file_b:
            click.echo(f"📂 Loading matrix B from: {file_b}")
            matrix_b = load_matrix_file(file_b)
        else:
            click.echo("📂 Using transpose of A as matrix B")
            matrix_b = [
                [matrix_a[j][i] for j in range(len(matrix_a))]
                for i in range(len(matrix_a[0]))
            ]

        b_rows, b_cols = len(matrix_b), len(matrix_b[0])
        click.echo(f"   Matrix B dimensions: {b_rows}x{b_cols}")

        # Verify dimensions
        if a_cols != b_rows:
            raise click.ClickException(
                f"Matrix dimensions incompatible: {a_rows}x{a_cols} * {b_rows}x{b_cols}"
            )
    else:
        # Demo mode with small matrices
        click.echo("\n🎯 Running demo with small 3x3 matrices...")
        matrix_a = [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9],
        ]
        matrix_b = [
            [9, 8, 7],
            [6, 5, 4],
            [3, 2, 1],
        ]

    a_rows = len(matrix_a)
    a_cols = len(matrix_a[0])
    b_rows = len(matrix_b)
    b_cols = len(matrix_b[0])

    click.echo(f"\n📊 Expected result dimensions: {a_rows}x{b_cols}")

    # Serialize input
    input_data = serialize_matrix(matrix_a, a_rows, a_cols)
    input_data += serialize_matrix(matrix_b, b_rows, b_cols)
    click.echo(f"📦 Serialized input: {len(input_data)} bytes")

    # Define the distributed matrix multiplication job
    @Job.define
    def distributed_matrix_multiply():
        @Job.split
        def split(data: bytes) -> List[bytes]:
            # Find where matrix A ends
            a_r, a_c = struct.unpack(">II", data[:8])
            a_size = 8 + a_r * a_c * 8

            matrix_a_data = data[:a_size]
            matrix_b_data = data[a_size:]

            ma, ar, ac = deserialize_matrix(matrix_a_data)
            mb, br, bc = deserialize_matrix(matrix_b_data)

            # Determine block size
            block_rows = max(1, ar // 4)
            block_cols = max(1, bc // 4)
            block_k = max(1, ac // 4)

            chunks = []
            for i in range(0, ar, block_rows):
                for j in range(0, bc, block_cols):
                    for k in range(0, ac, block_k):
                        a_block = []
                        for row in range(i, min(i + block_rows, ar)):
                            a_row = []
                            for col in range(k, min(k + block_k, ac)):
                                a_row.append(ma[row][col])
                            a_block.append(a_row)

                        b_block = []
                        for row in range(k, min(k + block_k, br)):
                            b_row = []
                            for col in range(j, min(j + block_cols, bc)):
                                b_row.append(mb[row][col])
                            b_block.append(b_row)

                        b_block_cols = (
                            len(b_block[0]) if b_block and len(b_block) > 0 else 0
                        )
                        chunk = struct.pack(">IIII", i, j, len(a_block), b_block_cols)
                        a_block_cols = (
                            len(a_block[0]) if a_block and len(a_block) > 0 else 0
                        )
                        chunk += serialize_matrix(a_block, len(a_block), a_block_cols)
                        chunk += serialize_matrix(b_block, len(b_block), b_block_cols)
                        chunks.append(chunk)

            return chunks

        @Job.execute
        def execute(chunk: bytes) -> bytes:
            i, j, a_rows_blk, b_cols_blk = struct.unpack(">IIII", chunk[:16])

            offset = 16
            block_a_header = chunk[offset : offset + 8]
            ba_rows, ba_cols = struct.unpack(">II", block_a_header)
            ba_size = 8 + ba_rows * ba_cols * 8
            block_a, _, _ = deserialize_matrix(chunk[offset : offset + ba_size])
            offset += ba_size

            block_b, _, _ = deserialize_matrix(chunk[offset:])

            result_block = matrix_multiply_block(block_a, block_b)

            result = struct.pack(">II", i, j)
            result += serialize_matrix(
                result_block,
                len(result_block),
                len(result_block[0]) if result_block else 0,
            )
            return result

        from typing import Dict, Tuple, Any

        @Job.merge
        def merge(results: List[bytes]) -> bytes:
            blocks: Dict[Tuple[int, int], List[List[Any]]] = {}
            max_i = 0
            max_j = 0

            for result in results:
                i, j = struct.unpack(">II", result[:8])
                matrix, rows, cols = deserialize_matrix(result[8:])

                key = (i, j)
                if key in blocks:
                    blocks[key] = add_matrices(blocks[key], matrix)
                else:
                    blocks[key] = matrix

                max_i = max(max_i, i + rows)
                max_j = max(max_j, j + cols)

            final_matrix = [[0.0 for _ in range(max_j)] for _ in range(max_i)]

            for (i, j), block in blocks.items():
                for bi, row in enumerate(block):
                    for bj, val in enumerate(row):
                        if i + bi < max_i and j + bj < max_j:
                            final_matrix[i + bi][j + bj] = val

            return serialize_matrix(final_matrix, max_i, max_j)

    job = distributed_matrix_multiply
    execution_mode = None
    worker_node = None
    result_data = None

    start_time = time.time()

    if connect:
        click.echo(f"\n🌐 Connecting to compute node at {host}:{port}...")

        # Log peer address if provided
        if peer_address:
            click.echo(f"   Using manual peer address: {peer_address[:50]}...")

        client = ComputeClient(host, port)
        connection_successful = False
        connection_error = None
        try:
            connection_successful = client.connect()
        except Exception as e:
            connection_error = str(e)

        if not connection_successful:
            click.echo(f"❌ Failed to connect to remote node at {host}:{port}")
            if connection_error:
                click.echo(f"   Connection error: {connection_error}")
            else:
                click.echo("   Unable to establish connection. Is the node running?")
            click.echo(
                "   For troubleshooting, try: ./scripts/check_network.sh --status"
            )
            click.echo("⚠️  FALLING BACK TO LOCAL EXECUTION")
            connect = False
        else:
            click.echo("✅ Successfully connected to remote node")

    if connect:
        execution_mode = "REMOTE"
        click.echo("\n⚡ Submitting job to DISTRIBUTED NETWORK...")
        click.echo(f"   Target: {host}:{port}")

        try:
            job_id = client.submit_job(job, input_data)
            click.echo("   ✅ Job submitted successfully")
            click.echo(f"   Job ID: {job_id}")

            click.echo("   Waiting for remote execution...")
            result_data, worker_node = client.get_result(job_id)
            click.echo("   ✅ Result received from remote node")
            client.disconnect()
        except Exception as e:
            click.echo(f"❌ Remote execution failed: {e}")
            click.echo("⚠️  FALLING BACK TO LOCAL EXECUTION")
            execution_mode = None
            connect = False

    if not connect:
        execution_mode = "LOCAL"
        click.echo("\n⚡ Running computation LOCALLY on this machine...")

        click.echo("\n--- SPLIT Phase ---")
        chunks = job.split(input_data)
        click.echo(f"   📊 Split into {len(chunks)} block multiplications")

        click.echo(f"\n--- EXECUTE Phase ({len(chunks)} blocks) ---")
        results = []
        for i, chunk in enumerate(chunks):
            result = job.execute(chunk)
            results.append(result)
            if (i + 1) % 10 == 0 or i == len(chunks) - 1:
                click.echo(f"   🔢 Computed block {i+1}/{len(chunks)}")

        click.echo("\n--- MERGE Phase ---")
        result_data = job.merge(results)
        click.echo("   ✅ Merged into final result matrix")

    elapsed = time.time() - start_time

    # Deserialize result
    result_matrix, r_rows, r_cols = deserialize_matrix(result_data)

    click.echo(f"\n{'=' * 60}")
    click.echo("✅ COMPUTATION COMPLETE")
    click.echo(f"{'=' * 60}")
    click.echo(f"   Result dimensions: {r_rows}x{r_cols}")
    click.echo(f"   Computation time: {elapsed:.3f} seconds")
    click.echo(f"   Result size: {len(result_data)} bytes")

    if execution_mode == "REMOTE":
        click.echo("   🌐 Execution Mode: REMOTE (distributed)")
        if worker_node and worker_node != "local":
            click.echo(f"      Executed by Worker: {worker_node}")
        else:
            click.echo(f"      Connected via: {host}:{port}")
    else:
        click.echo("   💻 Execution Mode: LOCAL (this machine)")

    # Save result if requested
    if output:
        save_matrix_file(output, result_matrix)
        click.echo(f"   💾 Saved to: {output}")

    # Verify with numpy if requested
    if verify:
        if has_numpy():
            click.echo("\n🔍 Verifying with NumPy...")
            matches, max_diff = verify_with_numpy(result_matrix, matrix_a, matrix_b)
            if matches:
                click.echo("   ✅ Result matches NumPy computation!")
            else:
                click.echo(
                    f"   ❌ Result differs from NumPy! Max difference: {max_diff}"
                )
        else:
            click.echo("\n⚠️  NumPy not installed, skipping verification")
            click.echo("   Install with: pip install numpy")

    # Show preview
    click.echo(f"\n{matrix_to_string(result_matrix)}")


# ============================================================================
# TEST COMMANDS - Easy execution of compute and communication tests
# ============================================================================


@cli.group()
def test():
    """Run tests for compute and communication."""
    pass


@test.command()
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
def all(host, port):
    """
    Run all tests (communication + compute).

    Example:
        python main.py test all
    """
    click.echo("\n🚀 Running All Tests")
    click.echo("=" * 60)

    # Run communication test
    ctx = click.get_current_context()
    ctx.invoke(communication, host=host, port=port)

    # Run compute test
    ctx.invoke(ces, host=host, port=port)

    click.echo("\n" + "=" * 60)
    click.echo("✅ All tests completed!")
    click.echo("=" * 60)


@test.command()
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
def communication(host, port):
    """
    Test P2P communication (connection, peers, metrics).

    Example:
        python main.py test communication
    """
    click.echo("\n📡 Communication Test")
    click.echo("=" * 60)

    client = GoNodeClient(host, port)
    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node at {host}:{port}")
        click.echo("   Make sure go-node is running:")
        click.echo(
            "   cd go && ./bin/go-node -node-id=1 -capnp-addr=:8080 -libp2p=true -local"
        )
        sys.exit(1)

    click.echo(f"✅ Connected to Go node at {host}:{port}")

    # Get nodes
    nodes = client.get_all_nodes()
    click.echo(f"\n📊 Found {len(nodes)} node(s):")
    for node in nodes:
        click.echo(
            f"   Node {node['id']}: latency={node['latencyMs']:.1f}ms, threat={node['threatScore']:.3f}"
        )

    # Get peers
    peers = client.get_connected_peers()
    click.echo(f"\n🔗 Connected peers: {peers}")

    # Network metrics
    metrics = client.get_network_metrics()
    if metrics:
        click.echo("\n📈 Network metrics:")
        click.echo(f"   Avg RTT: {metrics.get('avgRttMs', 0):.1f}ms")
        click.echo(f"   Bandwidth: {metrics.get('bandwidthMbps', 0):.1f} Mbps")
        click.echo(f"   Peer count: {metrics.get('peerCount', 0)}")

    client.disconnect()
    click.echo("\n✅ Communication test PASSED!")


@test.command()
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--size", default=5000, help="Test data size in bytes")
def ces(host, port, size):
    """
    Test CES compute pipeline (Compress → Encrypt → Shard).

    Example:
        python main.py test ces
        python main.py test ces --size 10000
    """
    click.echo("\n🖥️  CES Compute Test")
    click.echo("=" * 60)

    client = GoNodeClient(host, port)
    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node at {host}:{port}")
        sys.exit(1)

    click.echo("✅ Connected to Go node")

    # Generate test data
    test_data = b"Hello World! " * (size // 13 + 1)
    test_data = test_data[:size]
    click.echo(f"\n📦 Test data size: {len(test_data)} bytes")

    # CES process
    click.echo("\n🔄 Running CES process...")
    start = time.time()
    shards = client.ces_process(test_data, compression_level=3)
    elapsed = time.time() - start

    if shards is None:
        click.echo("❌ CES process failed")
        client.disconnect()
        sys.exit(1)

    total_size = sum(len(s) for s in shards)
    ratio = len(test_data) / total_size if total_size > 0 else 0

    click.echo(f"✅ Created {len(shards)} shards in {elapsed*1000:.1f}ms")
    click.echo(f"   Total shard size: {total_size} bytes")
    click.echo(f"   Compression ratio: {ratio:.2f}x")

    # Reconstruct
    click.echo("\n🔄 Reconstructing data...")
    start = time.time()
    shard_present = [True] * len(shards)
    reconstructed = client.ces_reconstruct(shards, shard_present, compression_level=3)
    elapsed = time.time() - start

    if reconstructed is None:
        click.echo("❌ CES reconstruct failed")
        client.disconnect()
        sys.exit(1)

    if reconstructed == test_data:
        click.echo(f"✅ Reconstructed in {elapsed*1000:.1f}ms")
        click.echo("✅ Data integrity verified!")
    else:
        click.echo(
            f"❌ Data mismatch! Original: {len(test_data)}, Reconstructed: {len(reconstructed)}"
        )
        client.disconnect()
        sys.exit(1)

    client.disconnect()
    click.echo("\n✅ CES compute test PASSED!")


@test.command()
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.argument("peer_address", required=False)
def manual_connect(host, port, peer_address):
    """
    Manually connect to a peer (use when mDNS fails).

    ONLY NEED IP:PORT - peer ID is auto-detected!

    Example:
        python main.py test manual-connect 192.168.1.100:9081
        python main.py test manual-connect 10.0.0.5:9081
        python main.py test manual-connect  # Interactive mode
    """

    # Connect to local Go node first
    click.echo("\n🔗 Manual Peer Connection")
    click.echo("=" * 60)

    client = GoNodeClient(host, port)
    if not client.connect():
        click.echo(f"\n❌ Failed to connect to local Go node at {host}:{port}")
        click.echo("\n📖 Make sure Go node is running:")
        click.echo(
            "   cd go && ./bin/go-node -node-id=1 -capnp-addr=:8080 -libp2p=true -local"
        )
        sys.exit(1)

    click.echo("✅ Connected to local node\n")

    # If no address provided, show interactive help
    if not peer_address:
        click.echo("📋 To connect to a remote node, you need:")
        click.echo("   1. The remote node's IP address")
        click.echo("   2. The remote node's libp2p port (usually 9081, 9082, etc.)\n")
        click.echo("📍 How to find this on the REMOTE MACHINE:")
        click.echo("   Run: ./go/bin/go-node -node-id=2 -capnp-addr=:8081 -libp2p=true")
        click.echo("   Look for a line with 'listening' or 'multiaddr'")
        click.echo("   Example: /ip4/192.168.1.100/tcp/9081/p2p/...\n")
        click.echo("📝 Copy the IP and port from that output\n")

        peer_address = click.prompt("Enter peer address (IP:port)", type=str)
        if not peer_address:
            click.echo("❌ Cancelled")
            client.disconnect()
            sys.exit(1)

    # Parse address
    if ":" not in peer_address:
        click.echo("❌ Invalid format. Use IP:port (e.g., 192.168.1.100:9081)")
        client.disconnect()
        sys.exit(1)

    try:
        peer_host, peer_port_str = peer_address.rsplit(":", 1)
        peer_port_num = int(peer_port_str)
    except ValueError:
        click.echo("❌ Invalid port number")
        client.disconnect()
        sys.exit(1)

    click.echo(f"🔍 Looking for peer at {peer_host}:{peer_port_num}...")

    # Try to auto-detect peer ID by trying different IDs (2-10)
    peer_id = None
    for candidate_id in range(2, 11):
        click.echo(f"   Trying peer ID {candidate_id}...", nl=False)
        success, quality = client.connect_to_peer(
            candidate_id, peer_host, peer_port_num
        )
        if success:
            peer_id = candidate_id
            click.echo(" ✅ Connected!")
            break
        else:
            click.echo(" ✗", nl=False)

    if peer_id is None:
        click.echo(f"\n\n❌ Could not connect to {peer_host}:{peer_port_num}")
        click.echo("\n🔧 Troubleshooting:")
        click.echo(f"   • Check the remote node is running on port {peer_port_num}")
        click.echo(f"   • Verify IP address is correct: ping {peer_host}")
        click.echo("   • Check firewall settings on both machines")
        click.echo("   • Try a different port (maybe 9082, 9083, etc.)")
        client.disconnect()
        sys.exit(1)

    # Show connection details
    click.echo(f"\n✅ Successfully connected to peer {peer_id}!")
    click.echo(f"   Address: {peer_host}:{peer_port_num}")
    quality = client.get_connection_quality(peer_id)
    if quality:
        click.echo("\n📊 Connection Quality:")
        click.echo(f"   Latency: {quality['latencyMs']:.1f}ms")
        click.echo(f"   Jitter: {quality['jitterMs']:.1f}ms")
        click.echo(f"   Packet Loss: {quality['packetLoss']*100:.2f}%")

    # Send test message
    click.echo("\n📤 Sending test message...")
    msg_success = client.send_message(peer_id, b"Hello from manual connection!")
    if msg_success:
        click.echo("✅ Test message sent!")
    else:
        click.echo("⚠️  Message send returned false (peer may not accept messages)")

    # Show status
    peers = client.get_connected_peers()
    click.echo(f"\n🔗 Connected peers: {peers}")

    click.echo("\n" + "=" * 60)
    click.echo("✅ Ready to use! Try:")
    click.echo("   - python main.py chat send <message>")
    click.echo("   - python main.py streaming start video")
    click.echo("=" * 60)

    client.disconnect()


@test.command()
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.argument("peer_id", default=2, type=int)
@click.option("--message", "-m", default="Hello from CLI!", help="Message to send")
def test_send(host, port, peer_id, message):
    """
    Send a test message to a peer.

    Example:
        python main.py test send 2
        python main.py test send 2 -m "Custom message"
    """
    client = GoNodeClient(host, port)
    if not client.connect():
        click.echo("❌ Failed to connect to Go node")
        sys.exit(1)

    click.echo(f"📤 Sending to node {peer_id}: {message}")

    if client.send_message(peer_id, message.encode()):
        click.echo("✅ Message sent!")
    else:
        click.echo("❌ Failed to send message")

    client.disconnect()


# ============================================================================
# DCDN Commands (Distributed CDN System)
# ============================================================================


@cli.group()
def dcdn():
    """
    DCDN (Distributed Content Delivery Network) commands.

    The DCDN module provides a complete distributed CDN implementation with:
    - QUIC Transport: Low-latency packet delivery
    - Reed-Solomon FEC: Forward error correction for packet recovery
    - P2P Mesh: Tit-for-tat incentive mechanism for fair bandwidth sharing
    - Ed25519 Verification: Cryptographic signature verification
    - Lock-free Ring Buffer: High-performance chunk storage

    The DCDN is primarily implemented in Rust for performance.
    These commands provide a convenient Python interface.

    Usage:
        python main.py dcdn demo
        python main.py dcdn info
    """
    pass


@dcdn.command()
def demo():
    """
    Run the interactive DCDN demo.

    This demonstrates the complete DCDN system:
    • ChunkStore (lock-free ring buffer)
    • FEC Engine (Reed-Solomon recovery)
    • P2P Engine (tit-for-tat bandwidth allocation)
    • Ed25519 signature verification
    • Complete chunk lifecycle

    Example:
        python main.py dcdn demo
    """
    click.echo("\n" + "=" * 60)
    click.echo("🌐 DCDN DEMO - Distributed CDN System")
    click.echo("=" * 60)
    click.echo("")
    click.echo("Running interactive DCDN demo from Rust implementation...")
    click.echo("")

    # Get project root by looking for marker file
    current = Path(__file__).parent
    while current != current.parent:
        if (current / "Cargo.toml").exists() or (current / ".git").exists():
            project_root = current
            break
        current = current.parent
    else:
        # Fallback to relative path if marker not found
        project_root = Path(__file__).parent.parent.parent

    rust_dir = project_root / "rust"

    if not rust_dir.exists():
        click.echo("❌ Rust directory not found", err=True)
        sys.exit(1)

    try:
        # Run the Rust DCDN demo
        subprocess.run(
            ["cargo", "run", "--example", "dcdn_demo"], cwd=str(rust_dir), check=True
        )
        click.echo("\n✅ DCDN demo completed successfully")

    except subprocess.CalledProcessError as e:
        click.echo(f"\n❌ DCDN demo failed: {e}", err=True)
        sys.exit(1)
    except FileNotFoundError:
        click.echo("\n❌ Cargo not found. Please install Rust:", err=True)
        click.echo(
            "   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
            err=True,
        )
        sys.exit(1)


@dcdn.command()
def info():
    """
    Show DCDN system information and capabilities.

    Displays information about the DCDN module including:
    - Architecture overview
    - Available components
    - Configuration options
    - Performance characteristics

    Example:
        python main.py dcdn info
    """
    click.echo("\n" + "=" * 60)
    click.echo("🌐 DCDN System Information")
    click.echo("=" * 60)
    click.echo("")

    click.echo("📋 Overview:")
    click.echo("   The DCDN (Distributed Content Delivery Network) module")
    click.echo("   provides a complete distributed CDN implementation.")
    click.echo("")

    click.echo("🔧 Components:")
    click.echo("   • QUIC Transport    - Low-latency packet delivery (quinn)")
    click.echo("   • FEC Engine        - Reed-Solomon forward error correction")
    click.echo("   • P2P Engine        - Tit-for-tat bandwidth allocation")
    click.echo("   • Signature Verifier - Ed25519 cryptographic verification")
    click.echo("   • ChunkStore        - Lock-free ring buffer storage")
    click.echo("")

    click.echo("⚡ Performance:")
    click.echo("   • Chunk lookup:      O(1) - constant time")
    click.echo("   • FEC encoding:      ~500 MB/s")
    click.echo("   • FEC decoding:      ~300 MB/s")
    click.echo("   • Storage:           >1 GB/s (lock-free, in-memory)")
    click.echo("   • Signature verify:  ~0.1 ms per chunk")
    click.echo("")

    click.echo("📁 Configuration:")
    click.echo("   Config file:   rust/config/dcdn.toml")
    click.echo("   Documentation: rust/src/dcdn/README.md")
    click.echo("")

    click.echo("🚀 Usage:")
    click.echo("   Run demo:      python main.py dcdn demo")
    click.echo("   Run tests:     cd rust && cargo test --test test_dcdn")
    click.echo("   From setup.sh: Option 20 - DCDN Demo")
    click.echo("")


@dcdn.command(name="test")
def dcdn_test():
    """
    Run DCDN unit tests.

    Runs the complete DCDN test suite from the Rust implementation.

    Example:
        python main.py dcdn test
    """
    click.echo("\n" + "=" * 60)
    click.echo("🧪 Running DCDN Tests")
    click.echo("=" * 60)
    click.echo("")

    # Get project root by looking for marker file
    current = Path(__file__).parent
    while current != current.parent:
        if (current / "Cargo.toml").exists() or (current / ".git").exists():
            project_root = current
            break
        current = current.parent
    else:
        # Fallback to relative path if marker not found
        project_root = Path(__file__).parent.parent.parent

    rust_dir = project_root / "rust"

    if not rust_dir.exists():
        click.echo("❌ Rust directory not found", err=True)
        sys.exit(1)

    try:
        click.echo("Running Rust DCDN test suite...\n")
        subprocess.run(
            ["cargo", "test", "--test", "test_dcdn"], cwd=str(rust_dir), check=True
        )
        click.echo("\n✅ All DCDN tests passed")

    except subprocess.CalledProcessError as e:
        click.echo(f"\n❌ Tests failed: {e}", err=True)
        sys.exit(1)
    except FileNotFoundError:
        click.echo("\n❌ Cargo not found. Please install Rust:", err=True)
        click.echo(
            "   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
            err=True,
        )
        sys.exit(1)


# ============================================================================
# Mandate 3 Commands Integration
# ============================================================================
try:
    from src.cli_mandate3 import register_mandate3_commands

    register_mandate3_commands(cli)
except ImportError as e:
    logger.warning(f"Mandate 3 commands not available: {e}")


if __name__ == "__main__":
    cli()
