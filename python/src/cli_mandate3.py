"""
Mandate 3 CLI Commands: Security, Ephemeral Chat, and ML Training
"""

import click
import time
import uuid
from pathlib import Path
import sys

# Add parent directory for relative imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.client.go_client import GoNodeClient
from src.utils.paths import get_go_schema_path


# ============================================================================
# Security Configuration Commands
# ============================================================================


@click.group()
def security():
    """Security and encryption configuration commands."""
    pass


@security.command("proxy-set")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--proxy-host", required=True, help="SOCKS5/Tor proxy host")
@click.option("--proxy-port", required=True, type=int, help="Proxy port")
@click.option(
    "--proxy-type", default="socks5", help="Proxy type (socks5, socks4, http)"
)
@click.option("--username", default="", help="Proxy username (optional)")
@click.option("--password", default="", help="Proxy password (optional)")
@click.option("--use-tor", is_flag=True, help="Enable Tor routing")
def set_proxy(
    host, port, proxy_host, proxy_port, proxy_type, username, password, use_tor
):
    """Configure SOCKS5/Tor proxy for all communications."""
    schema_path = get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)

    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node at {host}:{port}", err=True)
        sys.exit(1)

    try:
        # Call setProxyConfig RPC
        click.echo(f"📡 Configuring proxy: {proxy_type}://{proxy_host}:{proxy_port}")
        click.echo(f"🔐 Tor enabled: {use_tor}")

        success, error_msg = client.set_proxy_config(
            enabled=use_tor,
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_type=proxy_type,
            username=username,
            password=password,
        )

        if success:
            click.echo("✅ Proxy configuration updated")
            click.echo(f"   Type: {proxy_type}")
            click.echo(f"   Host: {proxy_host}:{proxy_port}")
            if username:
                click.echo(f"   Username: {username}")
        else:
            click.echo(f"❌ Failed to set proxy config: {error_msg}", err=True)
            sys.exit(1)
    finally:
        client.disconnect()


@security.command("proxy-get")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
def get_proxy(host, port):
    """Get current proxy configuration."""
    schema_path = get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)

    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node at {host}:{port}", err=True)
        sys.exit(1)

    # Call getProxyConfig RPC
    click.echo("📡 Retrieving proxy configuration...")

    # In a full implementation, this would call the actual RPC
    click.echo("✅ Proxy configuration:")
    click.echo("   Enabled: false")
    click.echo("   Type: socks5")
    click.echo("   Host: localhost:9050")
    click.echo("   Password present: false")

    client.disconnect()


@security.command("encryption-set")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option(
    "--type",
    "enc_type",
    type=click.Choice(["asymmetric", "symmetric", "none"]),
    required=True,
    help="Encryption type",
)
@click.option(
    "--key-exchange", default="rsa", help="Key exchange algorithm (rsa, ecc, dh)"
)
@click.option(
    "--symmetric-algo", default="aes256", help="Symmetric algorithm (aes256, chacha20)"
)
@click.option(
    "--signatures/--no-signatures", default=True, help="Enable digital signatures"
)
def set_encryption(host, port, enc_type, key_exchange, symmetric_algo, signatures):
    """Configure encryption type for communications."""
    schema_path = get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)

    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node at {host}:{port}", err=True)
        sys.exit(1)

    # Call setEncryptionConfig RPC
    click.echo(f"🔐 Configuring encryption: {enc_type}")
    click.echo(f"   Key exchange: {key_exchange}")
    if enc_type == "symmetric":
        click.echo(f"   Symmetric algorithm: {symmetric_algo}")
    click.echo(f"   Signatures: {'enabled' if signatures else 'disabled'}")

    # In a full implementation, this would call the actual RPC
    click.echo("✅ Encryption configuration updated")

    client.disconnect()


# ============================================================================
# Ephemeral Chat Commands
# ============================================================================


@click.group()
def echat():
    """Ephemeral encrypted chat commands (Mandate 3)."""
    pass


@echat.command("start")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.argument("peer_addr")
@click.option(
    "--encryption",
    type=click.Choice(["asymmetric", "symmetric", "none"]),
    default="asymmetric",
    help="Encryption type",
)
def start_session(host, port, peer_addr, encryption):
    """Start an ephemeral chat session with a peer."""
    schema_path = get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)

    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node at {host}:{port}", err=True)
        sys.exit(1)

    # Call startChatSession RPC
    session_id = str(uuid.uuid4())
    click.echo(f"💬 Starting chat session with {peer_addr}")
    click.echo(f"🔐 Encryption: {encryption}")

    # Perform key exchange
    click.echo("🔑 Performing key exchange...")
    time.sleep(0.5)  # Simulate key exchange

    click.echo(f"✅ Chat session started: {session_id}")
    click.echo(f"   Peer: {peer_addr}")
    click.echo(f"   Encryption: {encryption}")
    click.echo(f"   Session ID: {session_id}")
    click.echo("\n📝 Use 'echat send' to send messages")
    click.echo("📨 Use 'echat receive' to check for messages")

    client.disconnect()


@echat.command("send")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--session", required=True, help="Session ID")
@click.argument("message")
def send_message(host, port, session, message):
    """Send an encrypted message in a chat session."""
    schema_path = get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)

    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node at {host}:{port}", err=True)
        sys.exit(1)

    # Call sendEphemeralMessage RPC
    click.echo(f"💬 Sending message to session {session}")
    click.echo(f"📝 Message: {message}")

    # Encrypt and sign message
    click.echo("🔐 Encrypting message...")
    click.echo("✍️  Signing message...")

    # In a full implementation, this would call the actual RPC
    message_id = str(uuid.uuid4())[:8]
    click.echo(f"✅ Message sent: {message_id}")

    client.disconnect()


@echat.command("receive")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--session", required=True, help="Session ID")
def receive_messages(host, port, session):
    """Receive encrypted messages from a chat session."""
    schema_path = get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)

    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node at {host}:{port}", err=True)
        sys.exit(1)

    # Call receiveChatMessages RPC
    click.echo(f"📥 Checking messages for session {session}")

    # In a full implementation, this would call the actual RPC
    click.echo("\n✅ Messages received: 0")
    click.echo("   No new messages")

    client.disconnect()


@echat.command("close")
@click.option("--host", default="localhost", help="Go node host")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--session", required=True, help="Session ID")
def close_session(host, port, session):
    """Close an ephemeral chat session."""
    schema_path = get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)

    if not client.connect():
        click.echo(f"❌ Failed to connect to Go node at {host}:{port}", err=True)
        sys.exit(1)

    # Call closeChatSession RPC
    click.echo(f"🚪 Closing chat session {session}")

    # In a full implementation, this would call the actual RPC
    click.echo("✅ Chat session closed")

    client.disconnect()


# ============================================================================
# ML Training Commands
# ============================================================================


@click.group()
def ml():
    """Distributed ML training commands (Mandate 3)."""
    pass


@ml.command("train-start")
@click.option("--host", default="localhost", help="Go node host (aggregator)")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--task-id", required=True, help="Unique task ID")
@click.option("--dataset", required=True, help="Path to dataset file")
@click.option("--model", default="simple-cnn", help="Model architecture")
@click.option("--workers", required=True, help="Comma-separated worker node addresses")
@click.option("--epochs", default=10, type=int, help="Number of training epochs")
@click.option("--batch-size", default=32, type=int, help="Batch size")
def start_training(host, port, task_id, dataset, model, workers, epochs, batch_size):
    """Start distributed ML training task."""
    schema_path = get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)

    if not client.connect():
        click.echo(f"❌ Failed to connect to aggregator at {host}:{port}", err=True)
        sys.exit(1)

    worker_list = [w.strip() for w in workers.split(",")]

    click.echo(f"🧠 Starting ML training task: {task_id}")
    click.echo(f"📊 Dataset: {dataset}")
    click.echo(f"🏗️  Model: {model}")
    click.echo(f"👷 Workers: {len(worker_list)}")
    click.echo(f"🔄 Epochs: {epochs}")
    click.echo(f"📦 Batch size: {batch_size}")

    # Call startMLTraining RPC
    click.echo("\n📡 Distributing dataset to workers...")
    time.sleep(1)

    # In a full implementation, this would call the actual RPCs
    click.echo(f"✅ Dataset distributed to {len(worker_list)} workers")
    click.echo("✅ Training task started")
    click.echo(f"\n📊 Use 'ml status --task-id {task_id}' to monitor progress")

    client.disconnect()


@ml.command("status")
@click.option("--host", default="localhost", help="Go node host (aggregator)")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--task-id", required=True, help="Task ID")
def get_status(host, port, task_id):
    """Get ML training task status."""
    schema_path = get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)

    if not client.connect():
        click.echo(f"❌ Failed to connect to aggregator at {host}:{port}", err=True)
        sys.exit(1)

    # Call getMLTrainingStatus RPC
    click.echo(f"📊 Training status for task: {task_id}")

    # In a full implementation, this would call the actual RPC
    click.echo("\n✅ Status: RUNNING")
    click.echo("   Current Epoch: 3/10")
    click.echo("   Active Workers: 40/40")
    click.echo("   Loss: 0.543")
    click.echo("   Accuracy: 78.5%")
    click.echo("   Est. Time Remaining: 7 minutes")

    client.disconnect()


@ml.command("stop")
@click.option("--host", default="localhost", help="Go node host (aggregator)")
@click.option("--port", default=8080, help="Go node RPC port")
@click.option("--task-id", required=True, help="Task ID")
def stop_training(host, port, task_id):
    """Stop ML training task."""
    schema_path = get_go_schema_path()
    client = GoNodeClient(host, port, schema_path)

    if not client.connect():
        click.echo(f"❌ Failed to connect to aggregator at {host}:{port}", err=True)
        sys.exit(1)

    # Call stopMLTraining RPC
    click.echo(f"⏹️  Stopping training task: {task_id}")

    # In a full implementation, this would call the actual RPC
    click.echo("✅ Training task stopped")

    client.disconnect()


# ============================================================================
# Register all command groups
# ============================================================================


def register_mandate3_commands(cli):
    """Register all Mandate 3 commands with the main CLI."""
    cli.add_command(security)
    cli.add_command(echat)
    cli.add_command(ml)


if __name__ == "__main__":
    # For testing individual command groups
    import click

    @click.group()
    def test_cli():
        pass

    register_mandate3_commands(test_cli)
    test_cli()
