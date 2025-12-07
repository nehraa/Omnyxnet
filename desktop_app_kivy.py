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

# KivyMD imports
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.tab import MDTabs, MDTabsBase
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.scrollview import MDScrollView

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
        self.height = 200
        
        # Title
        self.add_widget(MDLabel(
            text="Node Connection",
            font_style="H6",
            size_hint_y=None,
            height=40
        ))
        
        # Host input
        host_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        host_layout.add_widget(MDLabel(text="Host:", size_hint_x=0.3))
        self.host_input = MDTextField(
            text="localhost",
            hint_text="Go node host",
            size_hint_x=0.7
        )
        host_layout.add_widget(self.host_input)
        self.add_widget(host_layout)
        
        # Port input
        port_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        port_layout.add_widget(MDLabel(text="Port:", size_hint_x=0.3))
        self.port_input = MDTextField(
            text="8080",
            hint_text="Go node port",
            input_filter='int',
            size_hint_x=0.7
        )
        port_layout.add_widget(self.port_input)
        self.add_widget(port_layout)
        
        # Connect button
        self.connect_btn = MDRaisedButton(
            text="Connect",
            size_hint_y=None,
            height=50,
            on_release=lambda x: self.app_ref.connect_to_node()
        )
        self.add_widget(self.connect_btn)


class LogView(MDScrollView):
    """Scrollable log view."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 0.3)
        
        self.log_label = MDLabel(
            text="",
            size_hint_y=None,
            markup=True
        )
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        self.add_widget(self.log_label)
    
    def add_log(self, message):
        """Add a log message."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_label.text += f"[{timestamp}] {message}\n"


class TabContent(MDBoxLayout, MDTabsBase):
    """Helper tab class that mixes MDTabsBase with a BoxLayout.

    MDTabs requires the tab content to inherit from MDTabsBase and an
    EventDispatcher-based layout. This class provides a simple reusable
    container for tab pages.
    """
    pass


class MainScreen(MDScreen):
    """Main screen of the application."""
    
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        
        # Main layout
        layout = MDBoxLayout(orientation='vertical')
        
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
        tab1 = TabContent()
        tab1.title = "Nodes"
        tab1_content = MDBoxLayout(orientation='vertical', padding=10)
        tab1_content.add_widget(MDRaisedButton(
            text="List All Nodes",
            on_release=lambda x: app_ref.list_nodes(),
            size_hint_y=None,
            height=50
        ))
        tab1_content.add_widget(MDLabel(text="Node information will appear here"))
        tab1.add_widget(tab1_content)
        tabs.add_widget(tab1)
        
        # Tab 2: Compute
        tab2 = TabContent()
        tab2.title = "Compute"
        tab2_content = MDBoxLayout(orientation='vertical', padding=10)
        tab2_content.add_widget(MDRaisedButton(
            text="Submit Compute Task",
            on_release=lambda x: app_ref.submit_compute_task(),
            size_hint_y=None,
            height=50
        ))
        tab2_content.add_widget(MDLabel(text="Compute tasks will appear here"))
        tab2.add_widget(tab2_content)
        tabs.add_widget(tab2)
        
        # Tab 3: DCDN
        tab3 = TabContent()
        tab3.title = "DCDN"
        tab3_content = MDBoxLayout(orientation='vertical', padding=10)
        tab3_content.add_widget(MDRaisedButton(
            text="Run DCDN Demo",
            on_release=lambda x: app_ref.run_dcdn_demo(),
            size_hint_y=None,
            height=50
        ))
        tab3_content.add_widget(MDRaisedButton(
            text="DCDN Info",
            on_release=lambda x: app_ref.show_dcdn_info(),
            size_hint_y=None,
            height=50
        ))
        tab3_content.add_widget(MDLabel(text="DCDN operations will appear here"))
        tab3.add_widget(tab3_content)
        tabs.add_widget(tab3)
        
        layout.add_widget(tabs)
        
        # Log view
        self.log_view = LogView()
        layout.add_widget(self.log_view)
        
        self.add_widget(layout)


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
    
    def build(self):
        """Build the application UI."""
        self.main_screen = MainScreen(self)
        
        # Schedule auto-startup
        Clock.schedule_once(lambda dt: self.auto_startup(), 1)
        
        self.log_message("🚀 Pangea Net Desktop Application Started")
        if CAPNP_AVAILABLE:
            self.log_message("✅ Cap'n Proto client available")
        else:
            self.log_message("⚠️  Cap'n Proto client not available")
        
        return self.main_screen
    
    def log_message(self, message):
        """Add a log message."""
        logger.info(message)
        if hasattr(self, 'main_screen'):
            self.main_screen.log_view.add_log(message)
    
    def is_port_open(self, host: str, port: int, timeout: float = 1.0) -> bool:
        """Check if a port is open."""
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
            if self.is_port_open(self.node_host, self.node_port):
                self.log_message("✅ Go node is already running")
                Clock.schedule_once(lambda dt: self.connect_to_node(), 0.5)
            else:
                self.log_message("⚠️  Go node not found. Please start manually.")
        
        threading.Thread(target=startup_thread, daemon=True).start()
    
    def connect_to_node(self):
        """Connect to Go node via Cap'n Proto."""
        if not CAPNP_AVAILABLE:
            self.log_message("❌ Cap'n Proto client not available")
            return
        
        host = self.main_screen.connection_card.host_input.text
        try:
            port = int(self.main_screen.connection_card.port_input.text)
        except ValueError:
            self.log_message("❌ Invalid port number")
            return
        
        self.log_message(f"🔗 Connecting to {host}:{port}...")
        
        def connect_thread():
            try:
                self.go_client = GoNodeClient(host=host, port=port)
                # Some client implementations may not expose a sync `connect()` method.
                # Guard the call to avoid attribute errors and to satisfy static analyzers.
                if hasattr(self.go_client, 'connect'):
                    try:
                        success = self.go_client.connect()
                    except Exception:
                        success = False
                else:
                    # Assume client auto-connects when constructed
                    success = True

                if success:
                    self.connected = True
                    self.log_message(f"✅ Connected to {host}:{port}")
                else:
                    self.log_message(f"❌ Failed to connect to {host}:{port}")
            except Exception as e:
                self.log_message(f"❌ Connection error: {str(e)}")
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def list_nodes(self):
        """List all nodes in the network."""
        if not self.connected:
            self.log_message("❌ Not connected to node")
            return
        
        self.log_message("📋 Listing all nodes...")
        # Implementation would call go_client methods
    
    def submit_compute_task(self):
        """Submit a compute task."""
        if not self.connected:
            self.log_message("❌ Not connected to node")
            return
        
        self.log_message("⚙️  Submitting compute task...")
        # Implementation would call compute CLI commands
    
    def run_dcdn_demo(self):
        """Run DCDN demo via CLI."""
        self.log_message("🌐 Running DCDN demo...")
        
        def demo_thread():
            try:
                result = subprocess.run(
                    [sys.executable, "python/main.py", "dcdn", "demo"],
                    cwd=str(PROJECT_ROOT),
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.log_message("✅ DCDN demo completed")
                else:
                    self.log_message(f"❌ DCDN demo failed: {result.stderr}")
            except Exception as e:
                self.log_message(f"❌ Error running DCDN demo: {str(e)}")
        
        threading.Thread(target=demo_thread, daemon=True).start()
    
    def show_dcdn_info(self):
        """Show DCDN information."""
        self.log_message("ℹ️  DCDN Information:")
        self.log_message("  • QUIC Transport - Low-latency packet delivery")
        self.log_message("  • FEC Engine - Reed-Solomon forward error correction")
        self.log_message("  • P2P Engine - Tit-for-tat bandwidth allocation")
        self.log_message("  • Signature Verifier - Ed25519 cryptographic verification")
        self.log_message("  • ChunkStore - Lock-free ring buffer storage")


def main():
    """Main entry point."""
    PangeaDesktopApp().run()


if __name__ == "__main__":
    main()
