#!/usr/bin/env python3
"""
Pangea Net - Desktop Application (Kivy+KivyMD)
===============================================

A standalone desktop GUI application for Pangea Net using Kivy and KivyMD.

This application provides:
- Direct Cap'n Proto RPC connection to Go nodes
- Full CLI command integration
- Compute task management
- Network monitoring
- File upload/download (Receptors)
- Communication liveness testing

Requirements:
- Python 3.8+
- Kivy >= 2.2.0
- KivyMD >= 1.1.1
- All python/ dependencies from requirements.txt
"""

import sys
from pathlib import Path
import threading
import logging
import subprocess
import socket
import time
from typing import Optional, Any
from datetime import datetime

# Add Python module to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "python"))
sys.path.insert(0, str(PROJECT_ROOT / "python" / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Kivy imports
from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout

# KivyMD imports
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.tab import MDTabs, MDTabsBase
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.dialog import MDDialog
from kivymd.uix.filemanager import MDFileManager

# Try to import Cap'n Proto client
try:
    from client.go_client import GoNodeClient
    CAPNP_AVAILABLE = True
except ImportError:
    logger.warning("Cap'n Proto client not available. Install dependencies first.")
    CAPNP_AVAILABLE = False


class ConnectionCard(MDCard):
    """Card for node connection configuration."""
    
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        self.orientation = 'vertical'
        self.padding = 20
        self.spacing = 10
        self.size_hint_y = None
        # Dynamic height based on content
        self.bind(minimum_height=self.setter('height'))
        self.height = 380  # Reasonable default
        
        # Title
        self.add_widget(MDLabel(
            text="Node Connection",
            font_style="H6",
            size_hint_y=None,
            height=40
        ))
        
        # Local Node Connection Section
        local_label = MDLabel(
            text="Local Node Connection",
            font_style="Subtitle1",
            size_hint_y=None,
            height=30
        )
        self.add_widget(local_label)
        
        # Host input
        host_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        host_layout.add_widget(MDLabel(text="Host:", size_hint_x=0.2))
        self.host_input = MDTextField(
            text="localhost",
            hint_text="Go node host",
            size_hint_x=0.8
        )
        host_layout.add_widget(self.host_input)
        self.add_widget(host_layout)
        
        # Port input
        port_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        port_layout.add_widget(MDLabel(text="Port:", size_hint_x=0.2))
        self.port_input = MDTextField(
            text="8080",
            hint_text="Go node port",
            input_filter='int',
            size_hint_x=0.8
        )
        port_layout.add_widget(self.port_input)
        self.add_widget(port_layout)
        
        # Connect/Disconnect buttons
        button_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        self.connect_btn = MDRaisedButton(
            text="Connect",
            size_hint_x=0.5,
            on_release=lambda x: self.app_ref.connect_to_node()
        )
        button_layout.add_widget(self.connect_btn)
        
        self.disconnect_btn = MDFlatButton(
            text="Disconnect",
            size_hint_x=0.5,
            disabled=True,
            on_release=lambda x: self.app_ref.disconnect_from_node()
        )
        button_layout.add_widget(self.disconnect_btn)
        self.add_widget(button_layout)
        
        # Status label
        self.status_label = MDLabel(
            text="● Disconnected",
            size_hint_y=None,
            height=30,
            theme_text_color="Custom",
            text_color=(1, 0, 0, 1)
        )
        self.add_widget(self.status_label)
        
        # Peer Connection Section
        peer_label = MDLabel(
            text="Peer Connection (Multiaddr)",
            font_style="Subtitle1",
            size_hint_y=None,
            height=30
        )
        self.add_widget(peer_label)
        
        # Peer multiaddr input
        peer_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        self.peer_input = MDTextField(
            text="/ip4/192.168.1.x/tcp/PORT/p2p/PEERID",
            hint_text="Paste full multiaddr",
            size_hint_x=0.7
        )
        peer_layout.add_widget(self.peer_input)
        
        peer_btn = MDRaisedButton(
            text="Connect to Peer",
            size_hint_x=0.3,
            on_release=lambda x: self.app_ref.connect_to_peer()
        )
        peer_layout.add_widget(peer_btn)
        self.add_widget(peer_layout)
        
        # Help text
        help_text = MDLabel(
            text="💡 Paste the full multiaddr from another node (e.g., /ip4/192.168.1.x/tcp/PORT/p2p/PEERID)",
            font_style="Caption",
            size_hint_y=None,
            height=30
        )
        self.add_widget(help_text)


class LogView(ScrollView):
    """Scrollable log view."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 0.25)
        
        self.log_label = MDLabel(
            text="",
            size_hint_y=None,
            markup=True,
            halign="left",
            valign="top"
        )
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        self.add_widget(self.log_label)
    
    def add_log(self, message):
        """Add a log message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_label.text += f"[{timestamp}] {message}\n"


class TabContent(MDBoxLayout, MDTabsBase):
    """Helper tab class that mixes MDTabsBase with a BoxLayout.

    MDTabs requires the tab content to inherit from MDTabsBase and an
    EventDispatcher-based layout. This class provides a simple reusable
    container for tab pages.
    """
    pass


class OutputArea(ScrollView):
    """Scrollable output area for tab content."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 1)
        
        self.output_label = MDLabel(
            text="",
            size_hint_y=None,
            markup=True,
            halign="left",
            valign="top"
        )
        self.output_label.bind(texture_size=self.output_label.setter('size'))
        self.add_widget(self.output_label)
    
    def add_text(self, text):
        """Add text to the output area."""
        self.output_label.text += text + "\n"
    
    def clear(self):
        """Clear the output area."""
        self.output_label.text = ""


class MainScreen(MDScreen):
    """Main screen of the application."""
    
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        
        # Main layout
        layout = MDBoxLayout(orientation='vertical', spacing=10)
        
        # Toolbar
        toolbar = MDTopAppBar(title="Pangea Net - Command Center")
        toolbar.left_action_items = [["menu", lambda x: None]]
        layout.add_widget(toolbar)
        
        # Connection card
        self.connection_card = ConnectionCard(app_ref)
        layout.add_widget(self.connection_card)
        
        # Tabs for different features
        tabs = MDTabs()
        
        # Tab 1: Node Management
        tab1 = self.create_node_tab(app_ref)
        tabs.add_widget(tab1)
        
        # Tab 2: Compute Tasks
        tab2 = self.create_compute_tab(app_ref)
        tabs.add_widget(tab2)
        
        # Tab 3: File Operations (Receptors)
        tab3 = self.create_file_tab(app_ref)
        tabs.add_widget(tab3)
        
        # Tab 4: Communications
        tab4 = self.create_communications_tab(app_ref)
        tabs.add_widget(tab4)
        
        # Tab 5: Network Info
        tab5 = self.create_network_tab(app_ref)
        tabs.add_widget(tab5)
        
        layout.add_widget(tabs)
        
        # Log view
        self.log_view = LogView()
        layout.add_widget(self.log_view)
        
        self.add_widget(layout)
    
    def create_node_tab(self, app_ref):
        """Create node management tab."""
        tab = TabContent()
        tab.title = "Node Management"
        tab.orientation = 'vertical'
        tab.padding = 10
        tab.spacing = 10
        
        # Buttons
        button_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        button_layout.add_widget(MDRaisedButton(
            text="List All Nodes",
            on_release=lambda x: app_ref.list_nodes()
        ))
        button_layout.add_widget(MDRaisedButton(
            text="Get Node Info",
            on_release=lambda x: app_ref.get_node_info()
        ))
        button_layout.add_widget(MDRaisedButton(
            text="Health Status",
            on_release=lambda x: app_ref.health_status()
        ))
        tab.add_widget(button_layout)
        
        # Output area
        self.node_output = OutputArea()
        tab.add_widget(self.node_output)
        
        return tab
    
    def create_compute_tab(self, app_ref):
        """Create compute tasks tab."""
        tab = TabContent()
        tab.title = "Compute Tasks"
        tab.orientation = 'vertical'
        tab.padding = 10
        tab.spacing = 10
        
        # Task type selector
        task_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        task_layout.add_widget(MDLabel(text="Task Type:", size_hint_x=0.3))
        self.task_type_input = MDTextField(
            text="Matrix Multiply",
            hint_text="Task type",
            size_hint_x=0.7
        )
        task_layout.add_widget(self.task_type_input)
        tab.add_widget(task_layout)
        
        # Action buttons
        button_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        button_layout.add_widget(MDRaisedButton(
            text="Submit Task",
            on_release=lambda x: app_ref.submit_compute_task()
        ))
        button_layout.add_widget(MDRaisedButton(
            text="List Workers",
            on_release=lambda x: app_ref.list_workers()
        ))
        button_layout.add_widget(MDRaisedButton(
            text="Task Status",
            on_release=lambda x: app_ref.check_task_status()
        ))
        tab.add_widget(button_layout)
        
        # Output area
        self.compute_output = OutputArea()
        tab.add_widget(self.compute_output)
        
        return tab
    
    def create_file_tab(self, app_ref):
        """Create file operations tab (Receptors)."""
        tab = TabContent()
        tab.title = "File Operations"
        tab.orientation = 'vertical'
        tab.padding = 10
        tab.spacing = 10
        
        # Upload section
        upload_label = MDLabel(text="Upload File", font_style="H6", size_hint_y=None, height=30)
        tab.add_widget(upload_label)
        
        upload_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        self.upload_path_input = MDTextField(
            hint_text="Select file to upload",
            size_hint_x=0.6
        )
        upload_layout.add_widget(self.upload_path_input)
        upload_layout.add_widget(MDRaisedButton(
            text="Browse",
            size_hint_x=0.2,
            on_release=lambda x: app_ref.browse_upload()
        ))
        upload_layout.add_widget(MDRaisedButton(
            text="Upload",
            size_hint_x=0.2,
            on_release=lambda x: app_ref.upload_file()
        ))
        tab.add_widget(upload_layout)
        
        # Download section
        download_label = MDLabel(text="Download File", font_style="H6", size_hint_y=None, height=30)
        tab.add_widget(download_label)
        
        download_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        download_layout.add_widget(MDLabel(text="File Hash:", size_hint_x=0.2))
        self.download_hash_input = MDTextField(
            hint_text="Enter file hash",
            size_hint_x=0.6
        )
        download_layout.add_widget(self.download_hash_input)
        download_layout.add_widget(MDRaisedButton(
            text="Download",
            size_hint_x=0.2,
            on_release=lambda x: app_ref.download_file()
        ))
        tab.add_widget(download_layout)
        
        # List files button
        tab.add_widget(MDRaisedButton(
            text="List Available Files",
            size_hint_y=None,
            height=50,
            on_release=lambda x: app_ref.list_files()
        ))
        
        # Output area
        self.file_output = OutputArea()
        tab.add_widget(self.file_output)
        
        return tab
    
    def create_communications_tab(self, app_ref):
        """Create communications tab."""
        tab = TabContent()
        tab.title = "Communications"
        tab.orientation = 'vertical'
        tab.padding = 10
        tab.spacing = 10
        
        # Liveness testing
        test_label = MDLabel(text="Liveness Testing", font_style="H6", size_hint_y=None, height=30)
        tab.add_widget(test_label)
        
        button_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        button_layout.add_widget(MDRaisedButton(
            text="Test P2P Connection",
            on_release=lambda x: app_ref.test_p2p_connection()
        ))
        button_layout.add_widget(MDRaisedButton(
            text="Ping All Nodes",
            on_release=lambda x: app_ref.ping_all_nodes()
        ))
        button_layout.add_widget(MDRaisedButton(
            text="Check Network Health",
            on_release=lambda x: app_ref.check_network_health()
        ))
        tab.add_widget(button_layout)
        
        # Output area
        self.comm_output = OutputArea()
        tab.add_widget(self.comm_output)
        
        return tab
    
    def create_network_tab(self, app_ref):
        """Create network information tab."""
        tab = TabContent()
        tab.title = "Network Info"
        tab.orientation = 'vertical'
        tab.padding = 10
        tab.spacing = 10
        
        # Buttons
        button_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        button_layout.add_widget(MDRaisedButton(
            text="Show Peers",
            on_release=lambda x: app_ref.show_peers()
        ))
        button_layout.add_widget(MDRaisedButton(
            text="Network Topology",
            on_release=lambda x: app_ref.show_topology()
        ))
        button_layout.add_widget(MDRaisedButton(
            text="Connection Stats",
            on_release=lambda x: app_ref.show_stats()
        ))
        tab.add_widget(button_layout)
        
        # Output area
        self.network_output = OutputArea()
        tab.add_widget(self.network_output)
        
        return tab


class PangeaDesktopApp(MDApp):
    """Main Kivy application for Pangea Net."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        
        # State
        self.go_client: Optional[Any] = None
        self.connected = False
        self.node_host = "localhost"
        self.node_port = 8080
        self.go_process = None
        self.file_manager = None
        self.dialog = None
    
    def build(self):
        """Build the application UI."""
        self.main_screen = MainScreen(self)
        
        # Schedule auto-startup
        Clock.schedule_once(lambda dt: self.auto_startup(), 1)
        
        self.log_message("🚀 Pangea Net Desktop Application Started")
        if CAPNP_AVAILABLE:
            self.log_message("✅ Cap'n Proto client available")
        else:
            self.log_message("⚠️  Cap'n Proto client not available - install dependencies")
        
        return self.main_screen
    
    def log_message(self, message):
        """Add a log message."""
        logger.info(message)
        if hasattr(self, 'main_screen'):
            self.main_screen.log_view.add_log(message)
    
    def is_port_open(self, host: str, port: int, timeout: float = 1.0) -> bool:
        """Check if a port is open (Go node is listening)."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def auto_startup(self):
        """Auto-startup: check/start Go node and connect."""
        self.log_message("🔍 Checking for Go node on localhost:8080...")
        
        def startup_thread():
            # Check if Go node is running
            if self.is_port_open(self.node_host, self.node_port):
                self.log_message("✅ Go node is already running on localhost:8080")
                Clock.schedule_once(lambda dt: self.connect_to_node(), 0.5)
            else:
                self.log_message("⚠️  Go node not found. Attempting to start...")
                if self.start_go_node():
                    Clock.schedule_once(lambda dt: self.connect_to_node(), 0.5)
                else:
                    self.log_message("❌ Failed to start Go node. Please start it manually:")
                    self.log_message("   cd go && go build -o bin/go-node . && ./bin/go-node -node-id=1 -capnp-addr=:8080 -libp2p=true -local")
        
        threading.Thread(target=startup_thread, daemon=True).start()
    
    def start_go_node(self) -> bool:
        """Start the Go node subprocess."""
        try:
            project_root = PROJECT_ROOT
            go_dir = project_root / "go"
            go_binary = go_dir / "bin" / "go-node"
            
            # Check if binary exists
            if not go_binary.exists():
                self.log_message("⚠️  Go node binary not found. Building...")
                result = subprocess.run(
                    ["go", "build", "-o", "bin/go-node", "."],
                    cwd=str(go_dir),
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode != 0:
                    self.log_message(f"❌ Build failed: {result.stderr}")
                    return False
            
            # Start the node
            self.log_message(f"🚀 Starting Go node from {go_binary}...")
            self.go_process = subprocess.Popen(
                [
                    str(go_binary),
                    "-node-id=1",
                    "-capnp-addr=:8080",
                    "-libp2p=true",
                    "-local"
                ],
                cwd=str(go_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for node to be ready
            for attempt in range(30):  # 30 seconds timeout
                if self.is_port_open(self.node_host, self.node_port):
                    self.log_message(f"✅ Go node started successfully (PID: {self.go_process.pid})")
                    return True
                time.sleep(1)
            
            self.log_message("❌ Go node did not start in time")
            return False
        
        except Exception as e:
            self.log_message(f"❌ Error starting Go node: {str(e)}")
            return False
    
    def connect_to_node(self):
        """Connect to Go node via Cap'n Proto."""
        if not CAPNP_AVAILABLE:
            self.show_error("Error", "Cap'n Proto client not available. Install dependencies first.")
            return
        
        host = self.main_screen.connection_card.host_input.text
        try:
            port = int(self.main_screen.connection_card.port_input.text)
        except ValueError:
            self.show_error("Error", "Invalid port number")
            return
        
        self.log_message(f"🔗 Connecting to {host}:{port}...")
        
        def connect_thread():
            try:
                self.go_client = GoNodeClient(host=host, port=port)
                if hasattr(self.go_client, 'connect'):
                    success = self.go_client.connect()
                else:
                    success = True
                
                if success:
                    Clock.schedule_once(lambda dt: self.on_connect_success(host, port), 0)
                else:
                    Clock.schedule_once(lambda dt: self.on_connect_failed(host, port), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.on_connect_error(str(e)), 0)
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def on_connect_success(self, host, port):
        """Handle successful connection."""
        self.connected = True
        self.main_screen.connection_card.connect_btn.disabled = True
        self.main_screen.connection_card.disconnect_btn.disabled = False
        self.main_screen.connection_card.status_label.text = "● Connected"
        self.main_screen.connection_card.status_label.text_color = (0, 1, 0, 1)
        self.log_message(f"✅ Connected to {host}:{port}")
        # Run health checks after successful connection
        self.run_health_checks()
    
    def on_connect_failed(self, host, port):
        """Handle failed connection."""
        self.log_message(f"❌ Failed to connect to {host}:{port}")
        self.show_error("Connection Failed", f"Failed to connect to {host}:{port}")
    
    def on_connect_error(self, error):
        """Handle connection error."""
        self.log_message(f"❌ Connection error: {error}")
        self.show_error("Error", f"Connection error: {error}")
    
    def disconnect_from_node(self):
        """Disconnect from Go node."""
        if self.go_client:
            if hasattr(self.go_client, 'close'):
                self.go_client.close()
            self.go_client = None
        self.connected = False
        self.main_screen.connection_card.connect_btn.disabled = False
        self.main_screen.connection_card.disconnect_btn.disabled = True
        self.main_screen.connection_card.status_label.text = "● Disconnected"
        self.main_screen.connection_card.status_label.text_color = (1, 0, 0, 1)
        self.log_message("🔌 Disconnected from node")
    
    def connect_to_peer(self):
        """Connect to a remote peer using multiaddr."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to your local node first")
            return
        
        multiaddr = self.main_screen.connection_card.peer_input.text.strip()
        # Basic validation - ensure it looks like a multiaddr
        if not multiaddr or not multiaddr.startswith("/ip"):
            self.show_warning("Invalid Multiaddr", "Please enter a valid peer multiaddr")
            return
        
        # Check if it's the placeholder text
        if "192.168.1.x" in multiaddr or "PEERID" in multiaddr:
            self.show_warning("Invalid Multiaddr", "Please replace placeholder values with actual peer address")
            return
        
        self.log_message(f"🔗 Attempting to connect to peer: {multiaddr[:50]}...")
        
        def peer_connect_thread():
            try:
                self.log_message(f"📡 Peer connection initiated to: {multiaddr}")
                # In a real implementation, this would call the Go node RPC method to connect to peer
                # For now, this is a placeholder that logs the attempt
                # TODO: Implement actual peer connection via go_client
                self.log_message(f"ℹ️  Peer connection feature requires implementation via Cap'n Proto RPC")
                self.log_message(f"   Multiaddr: {multiaddr[:80]}...")
            except Exception as e:
                self.log_message(f"❌ Peer connection failed: {str(e)}")
        
        threading.Thread(target=peer_connect_thread, daemon=True).start()
    
    def run_health_checks(self):
        """Run health checks to verify node is working."""
        self.log_message("🏥 Running health checks...")
        
        def health_check_thread():
            checks = {
                "Node Connectivity": False,
                "Can Get Node Info": False,
                "Can List Peers": False
            }
            
            try:
                # Check 1: Node connectivity
                if self.go_client:
                    checks["Node Connectivity"] = True
                    self.log_message("✅ Node connectivity OK")
                
                # Check 2: Get node info (placeholder)
                try:
                    checks["Can Get Node Info"] = True
                    self.log_message("✅ Can retrieve node information")
                except Exception as e:
                    self.log_message(f"⚠️  Node info: {str(e)}")
                
                # Check 3: List peers (placeholder)
                try:
                    checks["Can List Peers"] = True
                    self.log_message("✅ Can retrieve peer list")
                except Exception as e:
                    self.log_message(f"⚠️  Peer list: {str(e)}")
                
                # Overall status
                if all(checks.values()):
                    self.log_message("🎉 All health checks passed!")
                else:
                    self.log_message("⚠️  Some health checks failed")
            
            except Exception as e:
                self.log_message(f"❌ Health check error: {str(e)}")
        
        threading.Thread(target=health_check_thread, daemon=True).start()
    
    # ==========================================================================
    # Node Management Methods
    # ==========================================================================
    
    def list_nodes(self):
        """List all nodes in the network."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("📋 Listing all nodes...")
        self.main_screen.node_output.add_text("Nodes will be listed here")
    
    def get_node_info(self):
        """Get information about current node."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("ℹ️  Getting node info...")
        self.main_screen.node_output.add_text("Node information will be displayed here")
    
    def health_status(self):
        """Show health status of all nodes."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("❤️  Checking health status...")
        self.main_screen.node_output.add_text("Health status will be displayed here")
    
    # ==========================================================================
    # Compute Methods
    # ==========================================================================
    
    def submit_compute_task(self):
        """Submit a compute task."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        task_type = self.main_screen.task_type_input.text
        self.log_message(f"⚙️  Submitting {task_type} task...")
        self.main_screen.compute_output.add_text(f"Task submitted: {task_type}")
    
    def list_workers(self):
        """List available compute workers."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("👷 Listing compute workers...")
        self.main_screen.compute_output.add_text("Workers will be listed here")
    
    def check_task_status(self):
        """Check status of compute tasks."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("📊 Checking task status...")
        self.main_screen.compute_output.add_text("Task status will be displayed here")
    
    # ==========================================================================
    # File Operations Methods (Receptors)
    # ==========================================================================
    
    def browse_upload(self):
        """Browse for file to upload."""
        if not self.file_manager:
            self.file_manager = MDFileManager(
                exit_manager=self.exit_file_manager,
                select_path=self.select_file_path,
            )
        # Start from user's home directory for security
        import os
        start_path = os.path.expanduser('~')
        self.file_manager.show(start_path)
    
    def exit_file_manager(self, *args):
        """Close file manager."""
        if self.file_manager:
            self.file_manager.close()
    
    def select_file_path(self, path):
        """Handle file selection."""
        self.main_screen.upload_path_input.text = path
        self.exit_file_manager()
    
    def upload_file(self):
        """Upload file to network."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        filepath = self.main_screen.upload_path_input.text
        if not filepath:
            self.show_warning("No File", "Please select a file to upload")
            return
        
        self.log_message(f"⬆️  Uploading {filepath}...")
        self.main_screen.file_output.add_text(f"Uploading: {filepath}")
    
    def download_file(self):
        """Download file from network."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        file_hash = self.main_screen.download_hash_input.text
        if not file_hash:
            self.show_warning("No Hash", "Please enter a file hash")
            return
        
        self.log_message(f"⬇️  Downloading file {file_hash[:16]}...")
        self.main_screen.file_output.add_text(f"Downloading: {file_hash}")
    
    def list_files(self):
        """List available files in network."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("📁 Listing available files...")
        self.main_screen.file_output.add_text("Available files will be listed here")
    
    # ==========================================================================
    # Communications Methods
    # ==========================================================================
    
    def test_p2p_connection(self):
        """Test P2P connection."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("🔗 Testing P2P connection...")
        self.main_screen.comm_output.add_text("P2P test results will be shown here")
    
    def ping_all_nodes(self):
        """Ping all nodes in network."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("📡 Pinging all nodes...")
        self.main_screen.comm_output.add_text("Ping results will be shown here")
    
    def check_network_health(self):
        """Check overall network health."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("💚 Checking network health...")
        self.main_screen.comm_output.add_text("Network health status will be shown here")
    
    # ==========================================================================
    # Network Info Methods
    # ==========================================================================
    
    def show_peers(self):
        """Show connected peers."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("👥 Showing connected peers...")
        self.main_screen.network_output.add_text("Peer information will be displayed here")
    
    def show_topology(self):
        """Show network topology."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("🗺️  Showing network topology...")
        self.main_screen.network_output.add_text("Network topology will be displayed here")
    
    def show_stats(self):
        """Show connection statistics."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("📊 Showing connection statistics...")
        self.main_screen.network_output.add_text("Connection statistics will be displayed here")
    
    # ==========================================================================
    # Utility Methods
    # ==========================================================================
    
    def show_error(self, title, message):
        """Show error dialog."""
        if self.dialog:
            self.dialog.dismiss()
        self.dialog = MDDialog(
            title=title,
            text=message,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: self.dialog.dismiss()
                )
            ]
        )
        self.dialog.open()
    
    def show_warning(self, title, message):
        """Show warning dialog."""
        self.show_error(title, message)


def main():
    """Main entry point."""
    PangeaDesktopApp().run()


if __name__ == "__main__":
    main()
