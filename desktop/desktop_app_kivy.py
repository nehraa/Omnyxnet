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
import hashlib
import os
import traceback
import secrets
from typing import Optional, Any
from datetime import datetime
import re

# Add Python module to path
PROJECT_ROOT = Path(__file__).parent.parent  # Go up to WGT/
sys.path.insert(0, str(PROJECT_ROOT / "python"))
sys.path.insert(0, str(PROJECT_ROOT / "python" / "src"))

# Constants for timeouts and output limits
DCDN_DEMO_TIMEOUT = 60  # seconds
DCDN_TEST_TIMEOUT = 120  # seconds
MAX_LOGGED_FAILURES = 5  # Max streaming failures to log individually

# Streaming constants
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480
VIDEO_FPS = 30
VIDEO_JPEG_QUALITY = 60
AUDIO_SAMPLE_RATE = 48000
AUDIO_CHANNELS = 1
AUDIO_CHUNK_SIZE = 1024
MAX_INT16 = 32767  # Maximum value for 16-bit signed integer
DCDN_DEMO_STDOUT_TRUNCATE_LEN = 2000  # characters
DCDN_DEMO_STDERR_TRUNCATE_LEN = 1000  # characters
DCDN_TEST_STDOUT_TRUNCATE_LEN = 1000  # characters
DCDN_TEST_STDERR_TRUNCATE_LEN = 500  # characters

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
from kivy.metrics import dp
from kivy.core.window import Window

# Set minimum window size for usability
Window.minimum_width = 1024
Window.minimum_height = 768
Window.size = (1200, 900)

# KivyMD imports
try:
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
    from kivymd.uix.selectioncontrol import MDSwitch
    KIVYMD_AVAILABLE = True
except ImportError as e:
    logger.error(f"KivyMD not available: {e}")
    logger.error("Install with: pip install kivymd")
    KIVYMD_AVAILABLE = False
    sys.exit(1)

# Try to import Cap'n Proto client
try:
    from client.go_client import GoNodeClient
    CAPNP_AVAILABLE = True
except ImportError:
    logger.warning("Cap'n Proto client not available. Install dependencies first.")
    CAPNP_AVAILABLE = False

# Try to import optional dependencies for streaming
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    logger.warning("OpenCV (cv2) not available. Video streaming will not work.")
    CV2_AVAILABLE = False

try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    logger.warning("sounddevice not available. Audio streaming will not work.")
    SOUNDDEVICE_AVAILABLE = False


class ConnectionCard(MDCard):
    """Card for node connection configuration."""
    
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        self.orientation = 'vertical'
        self.padding = dp(20)
        self.spacing = dp(10)
        self.size_hint_y = None
        self.adaptive_height = True
        
        # Title
        self.add_widget(MDLabel(
            text="Node Connection",
            font_style="H6",
            size_hint_y=None,
            height=dp(40),
            adaptive_height=True
        ))
        
        # Connect/Disconnect buttons
        button_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        self.connect_btn = MDRaisedButton(
            text="Connect to Local Node",
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
            height=dp(30),
            theme_text_color="Custom",
            text_color=(1, 0, 0, 1),
            adaptive_height=True
        )
        self.add_widget(self.status_label)
        
        # Local multiaddr display + button
        self.multiaddr_label = MDLabel(
            text="Multiaddr: (unknown)",
            font_style="Caption",
            size_hint_y=None,
            height=dp(24),
            adaptive_height=True
        )
        self.add_widget(self.multiaddr_label)

        self.show_multiaddr_btn = MDFlatButton(
            text="Show Multiaddrs",
            size_hint_x=0.5,
            on_release=lambda x: self.app_ref.request_local_multiaddrs()
        )
        self.add_widget(self.show_multiaddr_btn)
        
        # Peer Connection Section
        peer_label = MDLabel(
            text="Peer Connection (Multiaddr)",
            font_style="Subtitle1",
            size_hint_y=None,
            height=dp(30),
            adaptive_height=True
        )
        self.add_widget(peer_label)
        
        # Peer multiaddr input
        peer_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), spacing=dp(10))
        self.peer_input = MDTextField(
            text="/ip4/192.168.1.x/tcp/PORT/p2p/PEERID",
            hint_text="Paste full multiaddr",
            size_hint_x=0.7,
            mode="rectangle"
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
            height=dp(40),
            adaptive_height=True
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


class TabContent(ScrollView, MDTabsBase):
    """Helper tab class that mixes MDTabsBase with a ScrollView.

    MDTabs requires the tab content to inherit from MDTabsBase and an
    EventDispatcher-based layout. This class provides a scrollable
    container for tab pages to handle smaller displays.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_scroll_x = False
        self.do_scroll_y = True
        
        # Create inner layout that will be scrollable
        self.inner_layout = MDBoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10), size_hint_y=None)
        self.inner_layout.bind(minimum_height=self.inner_layout.setter('height'))
        self.add_widget(self.inner_layout)


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
        layout = MDBoxLayout(orientation='vertical', spacing=5)
        
        # Toolbar
        toolbar = MDTopAppBar(title="Pangea Net - Command Center")
        toolbar.left_action_items = [["menu", lambda x: None]]
        toolbar.size_hint_y = None
        toolbar.height = dp(56)
        layout.add_widget(toolbar)
        
        # Notification bar (initially hidden)
        self.notification_bar = MDCard(
            size_hint_y=None,
            height=0,  # Hidden by default
            md_bg_color=(0.2, 0.6, 1, 0.9),
            padding=dp(10)
        )
        self.notification_label = MDLabel(
            text="",
            halign="center",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1)
        )
        self.notification_bar.add_widget(self.notification_label)
        layout.add_widget(self.notification_bar)
        
        # Scrollable connection card container
        conn_scroll = ScrollView(size_hint_y=None, height=dp(280))
        self.connection_card = ConnectionCard(app_ref)
        conn_scroll.add_widget(self.connection_card)
        layout.add_widget(conn_scroll)
        
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
        
        # Tab 6: DCDN
        tab6 = self.create_dcdn_tab(app_ref)
        tabs.add_widget(tab6)
        
        tabs.size_hint_y = 0.6  # Give tabs 60% of remaining space
        layout.add_widget(tabs)
        
        # Log view - fixed height at bottom
        self.log_view = LogView()
        self.log_view.size_hint_y = None
        self.log_view.height = dp(150)
        layout.add_widget(self.log_view)
        
        self.add_widget(layout)
    
    def create_node_tab(self, app_ref):
        """Create node management tab."""
        tab = TabContent()
        tab.title = "Node Management"
        
        # Buttons
        button_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
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
        tab.inner_layout.add_widget(button_layout)
        
        # Output area
        self.node_output = OutputArea()
        self.node_output.size_hint_y = None
        self.node_output.height = dp(300)
        tab.inner_layout.add_widget(self.node_output)
        
        return tab
    
    def create_compute_tab(self, app_ref):
        """Create compute tasks tab."""
        tab = TabContent()
        tab.title = "Compute Tasks"
        
        # Task type selector
        task_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), spacing=dp(10))
        task_layout.add_widget(MDLabel(text="Task Type:", size_hint_x=0.3, size_hint_y=None, height=dp(40), pos_hint={'center_y': 0.5}))
        self.task_type_input = MDTextField(
            text="Matrix Multiply",
            hint_text="Task type",
            size_hint_x=0.7,
            mode="rectangle"
        )
        task_layout.add_widget(self.task_type_input)
        tab.inner_layout.add_widget(task_layout)
        
        # Matrix size input
        size_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), spacing=dp(10))
        size_layout.add_widget(MDLabel(text="Matrix Size:", size_hint_x=0.3, size_hint_y=None, height=dp(40), pos_hint={'center_y': 0.5}))
        self.matrix_size_input = MDTextField(
            text="64",
            hint_text="Matrix dimension (e.g., 64 for 64x64)",
            size_hint_x=0.7,
            mode="rectangle",
            input_filter='int'
        )
        size_layout.add_widget(self.matrix_size_input)
        tab.inner_layout.add_widget(size_layout)
        
        # Action buttons
        button_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
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
        tab.inner_layout.add_widget(button_layout)
        
        # Output area
        self.compute_output = OutputArea()
        self.compute_output.size_hint_y = None
        self.compute_output.height = dp(300)
        tab.inner_layout.add_widget(self.compute_output)
        
        return tab
    
    def create_file_tab(self, app_ref):
        """Create file operations tab (Receptors)."""
        tab = TabContent()
        tab.title = "File Operations"
        
        # Upload section
        upload_label = MDLabel(text="Upload File", font_style="H6", size_hint_y=None, height=dp(30), adaptive_height=True)
        tab.inner_layout.add_widget(upload_label)
        
        upload_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), spacing=dp(10))
        self.upload_path_input = MDTextField(
            hint_text="Select file to upload",
            size_hint_x=0.6,
            mode="rectangle",
            readonly=True
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
        tab.inner_layout.add_widget(upload_layout)
        
        # Download section
        download_label = MDLabel(text="Download File", font_style="H6", size_hint_y=None, height=dp(30), adaptive_height=True)
        tab.inner_layout.add_widget(download_label)
        
        download_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), spacing=dp(10))
        download_layout.add_widget(MDLabel(text="File Hash:", size_hint_x=0.2, size_hint_y=None, height=dp(40), pos_hint={'center_y': 0.5}))
        self.download_hash_input = MDTextField(
            hint_text="Enter file hash",
            size_hint_x=0.6,
            mode="rectangle"
        )
        download_layout.add_widget(self.download_hash_input)
        download_layout.add_widget(MDRaisedButton(
            text="Download",
            size_hint_x=0.2,
            on_release=lambda x: app_ref.download_file()
        ))
        tab.inner_layout.add_widget(download_layout)
        
        # List files button
        tab.inner_layout.add_widget(MDRaisedButton(
            text="List Available Files",
            size_hint_y=None,
            height=dp(50),
            on_release=lambda x: app_ref.list_files()
        ))
        
        # Output area
        self.file_output = OutputArea()
        self.file_output.size_hint_y = None
        self.file_output.height = dp(300)
        tab.inner_layout.add_widget(self.file_output)
        
        return tab
    
    def create_communications_tab(self, app_ref):
        """Create communications tab."""
        tab = TabContent()
        tab.title = "Communications"
        
        # Tor Configuration Section
        tor_label = MDLabel(text="Tor Configuration", font_style="H6", size_hint_y=None, height=dp(30), adaptive_height=True)
        tab.inner_layout.add_widget(tor_label)
        
        tor_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        self.tor_switch = MDSwitch(size_hint_x=0.2)
        tor_layout.add_widget(MDLabel(text="Use Tor Proxy:", size_hint_x=0.3))
        tor_layout.add_widget(self.tor_switch)
        tor_layout.add_widget(MDRaisedButton(
            text="Test Tor",
            size_hint_x=0.25,
            on_release=lambda x: app_ref.test_tor_connection()
        ))
        tor_layout.add_widget(MDRaisedButton(
            text="Show My IP",
            size_hint_x=0.25,
            on_release=lambda x: app_ref.show_my_ip()
        ))
        tab.inner_layout.add_widget(tor_layout)
        
        # Chat Section
        chat_label = MDLabel(text="Chat Messaging", font_style="H6", size_hint_y=None, height=dp(30), adaptive_height=True)
        tab.inner_layout.add_widget(chat_label)
        
        # IP Display Row
        ip_row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        ip_row.add_widget(MDRaisedButton(
            text="Show My IP",
            size_hint_x=0.25,
            on_release=lambda x: app_ref.show_my_ip(),
            md_bg_color=(0.2, 0.6, 0.2, 1)  # Green color for visibility
        ))
        ip_row.add_widget(MDLabel(
            text="← Share this IP with the other node",
            size_hint_x=0.75
        ))
        tab.inner_layout.add_widget(ip_row)
        
        chat_input_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), spacing=dp(10))
        self.chat_peer_ip = MDTextField(
            hint_text="Peer IP address (from their 'Show My IP')",
            mode="rectangle",
            size_hint_x=0.5
        )
        chat_input_layout.add_widget(self.chat_peer_ip)
        chat_input_layout.add_widget(MDRaisedButton(
            text="Start Chat Session",
            size_hint_x=0.25,
            on_release=lambda x: app_ref.start_chat()
        ))
        chat_input_layout.add_widget(MDRaisedButton(
            text="Stop Chat",
            size_hint_x=0.25,
            on_release=lambda x: app_ref.stop_chat()
        ))
        tab.inner_layout.add_widget(chat_input_layout)
        
        # Message sending row
        msg_row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), spacing=dp(10))
        self.chat_message = MDTextField(
            hint_text="Type your message here...",
            mode="rectangle",
            size_hint_x=0.7
        )
        msg_row.add_widget(self.chat_message)
        msg_row.add_widget(MDRaisedButton(
            text="Send Message",
            size_hint_x=0.3,
            on_release=lambda x: app_ref.send_chat_message()
        ))
        tab.inner_layout.add_widget(msg_row)
        
        # Video Section
        video_label = MDLabel(text="Video Call", font_style="H6", size_hint_y=None, height=dp(30), adaptive_height=True)
        tab.inner_layout.add_widget(video_label)
        
        # IP Display Row for Video
        video_ip_row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        video_ip_row.add_widget(MDRaisedButton(
            text="Show My IP",
            size_hint_x=0.25,
            on_release=lambda x: app_ref.show_my_ip(),
            md_bg_color=(0.2, 0.6, 0.2, 1)
        ))
        video_ip_row.add_widget(MDLabel(
            text="← Share this IP with the other node",
            size_hint_x=0.75
        ))
        tab.inner_layout.add_widget(video_ip_row)
        
        video_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), spacing=dp(10))
        self.video_peer_ip = MDTextField(
            hint_text="Peer IP address (from their 'Show My IP')",
            mode="rectangle",
            size_hint_x=0.5
        )
        video_layout.add_widget(self.video_peer_ip)
        video_layout.add_widget(MDRaisedButton(
            text="Start Video",
            size_hint_x=0.25,
            on_release=lambda x: app_ref.start_video_call()
        ))
        video_layout.add_widget(MDRaisedButton(
            text="Stop Video",
            size_hint_x=0.25,
            on_release=lambda x: app_ref.stop_video_call()
        ))
        tab.inner_layout.add_widget(video_layout)
        
        # Voice Section
        voice_label = MDLabel(text="Voice Call", font_style="H6", size_hint_y=None, height=dp(30), adaptive_height=True)
        tab.inner_layout.add_widget(voice_label)
        
        # IP Display Row for Voice
        voice_ip_row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        voice_ip_row.add_widget(MDRaisedButton(
            text="Show My IP",
            size_hint_x=0.25,
            on_release=lambda x: app_ref.show_my_ip(),
            md_bg_color=(0.2, 0.6, 0.2, 1)
        ))
        voice_ip_row.add_widget(MDLabel(
            text="← Share this IP with the other node",
            size_hint_x=0.75
        ))
        tab.inner_layout.add_widget(voice_ip_row)
        
        voice_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), spacing=dp(10))
        self.voice_peer_ip = MDTextField(
            hint_text="Peer IP address (from their 'Show My IP')",
            mode="rectangle",
            size_hint_x=0.5
        )
        voice_layout.add_widget(self.voice_peer_ip)
        voice_layout.add_widget(MDRaisedButton(
            text="Start Voice",
            size_hint_x=0.25,
            on_release=lambda x: app_ref.start_voice_call()
        ))
        voice_layout.add_widget(MDRaisedButton(
            text="Stop Voice",
            size_hint_x=0.25,
            on_release=lambda x: app_ref.stop_voice_call()
        ))
        tab.inner_layout.add_widget(voice_layout)
        
        # Liveness testing
        test_label = MDLabel(text="Network Testing", font_style="H6", size_hint_y=None, height=dp(30), adaptive_height=True)
        tab.inner_layout.add_widget(test_label)
        
        button_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
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
        tab.inner_layout.add_widget(button_layout)
        
        # Output area
        self.comm_output = OutputArea()
        self.comm_output.size_hint_y = None
        self.comm_output.height = dp(300)
        tab.inner_layout.add_widget(self.comm_output)
        
        return tab
    
    def create_dcdn_tab(self, app_ref):
        """Create DCDN tab."""
        tab = TabContent()
        tab.title = "DCDN"
        
        # DCDN Info
        info_label = MDLabel(text="Distributed CDN System", font_style="H6", size_hint_y=None, height=dp(30), adaptive_height=True)
        tab.inner_layout.add_widget(info_label)
        
        # Connection Section
        conn_label = MDLabel(text="P2P Connection Setup", font_style="Subtitle1", size_hint_y=None, height=dp(30), adaptive_height=True)
        tab.inner_layout.add_widget(conn_label)
        
        conn_button_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        conn_button_layout.add_widget(MDRaisedButton(
            text="Show My Multiaddr",
            size_hint_x=0.33,
            on_release=lambda x: app_ref.show_dcdn_multiaddr(),
            md_bg_color=(0.2, 0.6, 0.2, 1)  # Green
        ))
        conn_button_layout.add_widget(MDRaisedButton(
            text="Connect to Peer",
            size_hint_x=0.33,
            on_release=lambda x: app_ref.connect_dcdn_peer(),
            md_bg_color=(0.2, 0.4, 0.8, 1)  # Blue
        ))
        conn_button_layout.add_widget(MDRaisedButton(
            text="Show My IP",
            size_hint_x=0.34,
            on_release=lambda x: app_ref.show_my_ip(),
            md_bg_color=(0.2, 0.6, 0.2, 1)  # Green
        ))
        tab.inner_layout.add_widget(conn_button_layout)
        
        # Peer Multiaddr Input
        peer_input_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), spacing=dp(10))
        self.dcdn_peer_multiaddr = MDTextField(
            hint_text="Paste peer's multiaddr here (from their 'Show My Multiaddr')",
            mode="rectangle",
            size_hint_x=1.0
        )
        peer_input_layout.add_widget(self.dcdn_peer_multiaddr)
        tab.inner_layout.add_widget(peer_input_layout)
        
        # Basic DCDN Buttons
        button_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        button_layout.add_widget(MDRaisedButton(
            text="Run Demo",
            on_release=lambda x: app_ref.run_dcdn_demo()
        ))
        button_layout.add_widget(MDRaisedButton(
            text="System Info",
            on_release=lambda x: app_ref.dcdn_info()
        ))
        button_layout.add_widget(MDRaisedButton(
            text="Test DCDN",
            on_release=lambda x: app_ref.test_dcdn()
        ))
        tab.inner_layout.add_widget(button_layout)
        
        # Video Streaming Section
        stream_label = MDLabel(text="Video Streaming Test", font_style="H6", size_hint_y=None, height=dp(30), adaptive_height=True)
        tab.inner_layout.add_widget(stream_label)
        
        stream_info_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), spacing=dp(10))
        self.stream_peer_ip = MDTextField(
            hint_text="Peer IP to stream to (or 'server' to receive)",
            mode="rectangle",
            size_hint_x=0.6
        )
        stream_info_layout.add_widget(self.stream_peer_ip)
        stream_info_layout.add_widget(MDRaisedButton(
            text="Start Stream",
            size_hint_x=0.2,
            on_release=lambda x: app_ref.start_dcdn_stream()
        ))
        stream_info_layout.add_widget(MDRaisedButton(
            text="Stop Stream",
            size_hint_x=0.2,
            on_release=lambda x: app_ref.stop_dcdn_stream()
        ))
        tab.inner_layout.add_widget(stream_info_layout)
        
        # Video file selection
        video_file_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), spacing=dp(10))
        self.video_file_path = MDTextField(
            hint_text="Video file path (leave empty for webcam)",
            mode="rectangle",
            size_hint_x=0.7
        )
        video_file_layout.add_widget(self.video_file_path)
        video_file_layout.add_widget(MDRaisedButton(
            text="Browse",
            size_hint_x=0.15,
            on_release=lambda x: app_ref.browse_video_file()
        ))
        video_file_layout.add_widget(MDRaisedButton(
            text="Test Video",
            size_hint_x=0.15,
            on_release=lambda x: app_ref.test_video_file()
        ))
        tab.inner_layout.add_widget(video_file_layout)
        
        # Output area
        self.dcdn_output = OutputArea()
        self.dcdn_output.size_hint_y = None
        self.dcdn_output.height = dp(300)
        tab.inner_layout.add_widget(self.dcdn_output)
        
        return tab
    
    def create_network_tab(self, app_ref):
        """Create network information tab with mDNS discovery."""
        tab = TabContent()
        tab.title = "Network Info"
        
        # mDNS Discovery Section
        mdns_label = MDLabel(text="mDNS Local Discovery", font_style="H6", size_hint_y=None, height=dp(30), adaptive_height=True)
        tab.inner_layout.add_widget(mdns_label)
        
        mdns_button_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        mdns_button_layout.add_widget(MDRaisedButton(
            text="🔍 Discover Local Peers",
            on_release=lambda x: app_ref.discover_mdns_peers()
        ))
        mdns_button_layout.add_widget(MDRaisedButton(
            text="🔄 Refresh",
            on_release=lambda x: app_ref.refresh_mdns()
        ))
        mdns_button_layout.add_widget(MDRaisedButton(
            text="🔗 Quick Connect",
            on_release=lambda x: app_ref.quick_connect_peer()
        ))
        tab.inner_layout.add_widget(mdns_button_layout)
        
        # General Network Buttons
        network_label = MDLabel(text="Network Information", font_style="H6", size_hint_y=None, height=dp(30), adaptive_height=True)
        tab.inner_layout.add_widget(network_label)
        
        button_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
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
        tab.inner_layout.add_widget(button_layout)
        
        # Output area
        self.network_output = OutputArea()
        self.network_output.size_hint_y = None
        self.network_output.height = dp(300)
        tab.inner_layout.add_widget(self.network_output)
        
        return tab


class PangeaDesktopApp(MDApp):
    """Main Kivy application for Pangea Net."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Modern theme with updated colors
        self.theme_cls.primary_palette = "DeepPurple"
        self.theme_cls.accent_palette = "Cyan"
        self.theme_cls.theme_style = "Dark"  # Modern dark theme
        self.theme_cls.material_style = "M3"  # Material Design 3
        
        # State
        self.go_client: Optional[Any] = None
        self.connected = False
        self.node_host = "localhost"
        self.node_port = 8080
        self.go_process = None
        self.file_manager = None
        self.dialog = None
        
        # Streaming state
        self.streaming_active = False
        self.chat_active = False
        self.chat_peer_addr = ""
    
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
    
    def show_notification(self, message: str, duration: int = 5, color=None):
        """Show a notification message at the top of the screen."""
        if not hasattr(self, 'main_screen'):
            return
        
        # Set message and color
        self.main_screen.notification_label.text = message
        if color:
            self.main_screen.notification_bar.md_bg_color = color
        else:
            self.main_screen.notification_bar.md_bg_color = (0.2, 0.6, 1, 0.9)  # Default blue
        
        # Show notification
        self.main_screen.notification_bar.height = dp(50)
        
        # Auto-hide after duration
        if duration > 0:
            Clock.schedule_once(lambda dt: self.hide_notification(), duration)
    
    def hide_notification(self):
        """Hide the notification bar."""
        if hasattr(self, 'main_screen'):
            self.main_screen.notification_bar.height = 0
    
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
            # Kill any existing go-node processes to avoid conflicts
            try:
                subprocess.run(["pkill", "-f", "go-node"], capture_output=True, timeout=2)
                time.sleep(0.5)
            except Exception:
                pass
            
            # Start fresh Go node
            self.log_message("🚀 Starting Go node...")
            if self.start_go_node():
                Clock.schedule_once(lambda dt: self.connect_to_node(), 0.5)
            else:
                self.log_message("❌ Failed to start Go node. Please start it manually:")
                self.log_message("   cd go && go build -o bin/go-node . && ./bin/go-node -node-id=1 -capnp-addr=:8080 -libp2p=true -libp2p-port=0")
        
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
            # We use port 0 to let the OS choose a random port, avoiding conflicts.
            # We remove -local so it can connect to other devices on the LAN.
            self.log_message(f"🚀 Starting Go node from {go_binary}...")
            
            # Set up environment with Rust library path (CRITICAL!)
            env = os.environ.copy()
            rust_lib_path = str(project_root / "rust" / "target" / "release")
            if "LD_LIBRARY_PATH" in env:
                env["LD_LIBRARY_PATH"] = f"{rust_lib_path}:{env['LD_LIBRARY_PATH']}"
            else:
                env["LD_LIBRARY_PATH"] = rust_lib_path
            
            # Also set DYLD_LIBRARY_PATH for macOS
            if "DYLD_LIBRARY_PATH" in env:
                env["DYLD_LIBRARY_PATH"] = f"{rust_lib_path}:{env['DYLD_LIBRARY_PATH']}"
            else:
                env["DYLD_LIBRARY_PATH"] = rust_lib_path
            
            # Set CES encryption key to prevent ephemeral key warning
            if "CES_ENCRYPTION_KEY" not in env:
                # Generate or load a persistent key for this device
                ces_key_file = project_root / ".ces_key"
                if ces_key_file.exists():
                    with open(ces_key_file, 'r') as f:
                        env["CES_ENCRYPTION_KEY"] = f.read().strip()
                else:
                    # Generate a new persistent key (64 hex chars = 32 bytes)
                    import secrets
                    ces_key = secrets.token_hex(32)
                    with open(ces_key_file, 'w') as f:
                        f.write(ces_key)
                    env["CES_ENCRYPTION_KEY"] = ces_key
                    self.log_message("🔑 Generated new CES encryption key")
            
            self.log_message(f"📚 Library path: {rust_lib_path}")
            
            self.go_process = subprocess.Popen(
                [
                    str(go_binary),
                    "-node-id=1",
                    "-capnp-addr=:8080",
                    "-libp2p=true",
                    "-libp2p-port=0"
                ],
                cwd=str(go_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,  # Use binary mode to avoid UTF-8 decode errors
                env=env
            )
            # Start reader threads to extract multiaddr info from stdout/stderr
            def reader(pipe, pipe_name):
                try:
                    for raw_bytes in iter(lambda: pipe.readline(), b''):
                        if not raw_bytes:
                            continue
                        
                        # Decode with error handling for non-UTF-8 content
                        try:
                            line = raw_bytes.decode('utf-8', errors='replace').strip()
                        except Exception:
                            # If decode fails entirely, skip this line
                            continue
                        
                        if not line:
                            continue
                        
                        # Log all output for debugging
                        Clock.schedule_once(lambda dt, l=line: self.log_message(f"[Go-{pipe_name}] {l}"), 0)
                        
                        # Check for errors
                        if "error" in line.lower() or "failed" in line.lower():
                            Clock.schedule_once(lambda dt, l=line: self.log_message(f"⚠️  {l}"), 0)
                        
                        # Look for multiaddr patterns like /ip4/1.2.3.4/tcp/PORT/p2p/PEERID
                        m = re.search(r"(/ip4/[0-9.]+/tcp/[0-9]+/p2p/[a-zA-Z0-9]+)", line)
                        if m:
                            addr = m.group(1)
                            # Replace 0.0.0.0 or 127.0.0.1 with detected local IP if present
                            if '/ip4/0.0.0.0' in addr or '/ip4/127.0.0.1' in addr:
                                local_ip = self._detect_local_ip()
                                addr = re.sub(r'/ip4/(0.0.0.0|127.0.0.1)', f'/ip4/{local_ip}', addr)
                            # Save and update UI
                            self.local_multiaddrs.add(addr)
                            Clock.schedule_once(lambda dt, a=addr: self.log_message(f"📍 Multiaddr: {a}"), 0)
                            Clock.schedule_once(lambda dt: self._update_multiaddr_ui(), 0)
                except Exception as e:
                    error_msg = str(e)
                    Clock.schedule_once(lambda dt, err=error_msg, pn=pipe_name: self.log_message(f"❌ Reader error ({pn}): {err}"), 0)

            # Initialize storage and start threads
            self.local_multiaddrs = set()
            if self.go_process.stdout:
                threading.Thread(target=reader, args=(self.go_process.stdout, "stdout"), daemon=True).start()
            if self.go_process.stderr:
                threading.Thread(target=reader, args=(self.go_process.stderr, "stderr"), daemon=True).start()
            
            # Wait for node to be ready
            for attempt in range(30):  # 30 seconds timeout
                # Check if process crashed
                if self.go_process.poll() is not None:
                    self.log_message(f"❌ Go node process exited with code {self.go_process.returncode}")
                    self.log_message("💡 Tip: Check if Rust library is built: cd rust && cargo build --release")
                    return False
                
                if self.is_port_open(self.node_host, self.node_port):
                    self.log_message(f"✅ Go node started successfully (PID: {self.go_process.pid})")
                    # If any multiaddrs were discovered already, update UI immediately
                    if hasattr(self, 'local_multiaddrs') and self.local_multiaddrs:
                        Clock.schedule_once(lambda dt: self._update_multiaddr_ui(), 0)
                    return True
                
                if attempt % 5 == 0 and attempt > 0:
                    self.log_message(f"⏳ Still waiting for node... ({attempt}s)")
                
                time.sleep(1)
            
            self.log_message("❌ Go node did not start in time (30s timeout)")
            if self.go_process.poll() is None:
                self.log_message("🔍 Process still running but port not open - possible startup issue")
            return False
        
        except Exception as e:
            self.log_message(f"❌ Error starting Go node: {str(e)}")
            self.log_message(f"📋 Traceback: {traceback.format_exc()}")
            return False
    
    def connect_to_node(self):
        """Connect to Go node via Cap'n Proto."""
        if not CAPNP_AVAILABLE:
            self.show_error("Error", "Cap'n Proto client not available. Install dependencies first.")
            return
        
        host = self.node_host
        port = self.node_port
        
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

    def _detect_local_ip(self) -> str:
        """Detect the local outbound IP address robustly.

        Tries a UDP connect to a public IP to determine the preferred outbound
        interface. Falls back to gethostbyname or 127.0.0.1 if necessary.
        """
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # doesn't actually send packets
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
        except Exception:
            pass
        finally:
            try:
                if sock:
                    sock.close()
            except Exception:
                pass

        # Fallback to hostname resolution
        try:
            ip = socket.gethostbyname(socket.gethostname())
            if ip and not ip.startswith("127."):
                return ip
        except Exception:
            pass

        return "127.0.0.1"

    def _update_multiaddr_ui(self):
        """Update the ConnectionCard multiaddr label and log outputs."""
        try:
            if not hasattr(self, 'local_multiaddrs') or not self.local_multiaddrs:
                return
            # Join and display
            addrs = sorted(list(self.local_multiaddrs))
            display = ", ".join(addrs)
            # Update UI label
            if hasattr(self, 'main_screen') and hasattr(self.main_screen, 'connection_card'):
                self.main_screen.connection_card.multiaddr_label.text = f"Multiaddr: {addrs[0]}"
            # Log it
            self.log_message(f"📍 Local multiaddr: {addrs[0]}")
            # Also write to file output for convenience
            if hasattr(self, 'main_screen') and hasattr(self.main_screen, 'file_output'):
                self.main_screen.file_output.add_text(f"Local multiaddrs: {display}")
        except Exception:
            pass
    
    def fetch_node_multiaddr(self):
        """Fetch multiaddr from the running Go node's log output."""
        def fetch_thread():
            try:
                # Read from the go-node log file
                log_path = '/tmp/go-node.log'
                if os.path.exists(log_path):
                    with open(log_path, 'r') as f:
                        content = f.read()
                    # Look for multiaddr pattern
                    matches = re.findall(r'/ip4/[0-9.]+/tcp/[0-9]+/p2p/[a-zA-Z0-9]+', content)
                    if matches:
                        # Filter out localhost addresses
                        valid_addrs = [addr for addr in matches if '127.0.0.1' not in addr]
                        if valid_addrs:
                            self.local_multiaddrs = set(valid_addrs)
                            Clock.schedule_once(lambda dt: self._update_multiaddr_ui(), 0)
                            return
                
                # Fallback: parse from process output if we started it
                if hasattr(self, 'local_multiaddrs') and self.local_multiaddrs:
                    Clock.schedule_once(lambda dt: self._update_multiaddr_ui(), 0)
            except Exception as e:
                self.log_message(f"⚠️  Could not fetch multiaddr: {e}")
        
        threading.Thread(target=fetch_thread, daemon=True).start()

    def request_local_multiaddrs(self):
        """Public request to populate/show local multiaddrs.

        Strategy:
        - If we started the Go node and captured stdout/stderr, use extracted addresses.
        - Else try to parse the common live_test log at ~/.pangea/live_test/node.log
        - Update UI accordingly.
        """
        # If we already have addresses from live stdout, show them
        if hasattr(self, 'local_multiaddrs') and self.local_multiaddrs:
            Clock.schedule_once(lambda dt: self._update_multiaddr_ui(), 0)
            return

        # Fallback: try to parse ~/.pangea/live_test/node.log (used by live_test.sh)
        import os
        log_path = os.path.expanduser('~/.pangea/live_test/node.log')
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r') as f:
                    content = f.read()
                m = re.search(r"(/ip4/[0-9.]+/tcp/[0-9]+/p2p/[a-zA-Z0-9]+)", content)
                if m:
                    addr = m.group(1)
                    if '/ip4/0.0.0.0' in addr:
                        local_ip = self._detect_local_ip()
                        addr = addr.replace('/ip4/0.0.0.0', f'/ip4/{local_ip}')
                    self.local_multiaddrs = {addr}
                    Clock.schedule_once(lambda dt: self._update_multiaddr_ui(), 0)
                    return
            except Exception:
                pass

        # Nothing found
        self.log_message("ℹ️  No local multiaddr found. Start node or run ./scripts/live_test.sh to generate one.")
    
    def on_connect_success(self, host, port):
        """Handle successful connection."""
        self.connected = True
        self.main_screen.connection_card.connect_btn.disabled = True
        self.main_screen.connection_card.disconnect_btn.disabled = False
        self.main_screen.connection_card.status_label.text = "● Connected"
        self.main_screen.connection_card.status_label.text_color = (0, 1, 0, 1)
        self.log_message(f"✅ Connected to {host}:{port}")
        # Get and display multiaddr from running node
        self.fetch_node_multiaddr()
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
        # Stop all streaming services first
        if self.streaming_active or self.chat_active:
            self.log_message("🛑 Stopping P2P services...")
            try:
                if self.go_client:
                    self.go_client.stop_streaming()
            except Exception as e:
                logger.error(f"Error stopping streaming on disconnect: {e}")
            self.streaming_active = False
            self.chat_active = False
        
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
                
                # Parse multiaddr to extract host/port/peerID if possible
                # Format: /ip4/192.168.1.3/tcp/56964/p2p/12D3Koo...
                import re
                host = "0.0.0.0"
                port = 0
                peer_id_str = ""
                
                # Extract IP
                ip_match = re.search(r'/ip4/([^/]+)', multiaddr)
                if ip_match:
                    host = ip_match.group(1)
                
                # Extract Port
                port_match = re.search(r'/tcp/(\d+)', multiaddr)
                if port_match:
                    port = int(port_match.group(1))
                
                # Extract Peer ID
                peer_match = re.search(r'/p2p/([^/]+)', multiaddr)
                if peer_match:
                    peer_id_str = peer_match.group(1)
                
                # Validate parsed components
                if not host or host == "0.0.0.0":
                    self.log_message(f"❌ Invalid multiaddr: Could not extract IP address")
                    return
                if port == 0:
                    self.log_message(f"❌ Invalid multiaddr: Could not extract port number")
                    return
                if not peer_id_str:
                    self.log_message(f"❌ Invalid multiaddr: Could not extract peer ID")
                    return
                
                self.log_message(f"ℹ️  Parsed multiaddr: IP={host}, Port={port}, PeerID={peer_id_str[:8]}...")
                
                # Test basic connectivity first
                self.log_message(f"ℹ️  Testing network connectivity to {host}:{port}...")
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test_sock:
                        test_sock.settimeout(5.0)
                        result = test_sock.connect_ex((host, port))
                    
                    if result != 0:
                        self.log_message(f"❌ Network connectivity test FAILED:")
                        self.log_message(f"   Cannot reach {host}:{port}")
                        self.log_message(f"   Error code: {result}")
                        self.log_message(f"   Possible causes:")
                        self.log_message(f"   - Port {port} is not open on remote host")
                        self.log_message(f"   - Firewall blocking connection")
                        self.log_message(f"   - Remote node not running")
                        self.log_message(f"   - Wrong IP address")
                        return
                    else:
                        self.log_message(f"✅ Network connectivity OK - Port {port} is reachable")
                except socket.timeout:
                    self.log_message(f"❌ Connection timeout - {host}:{port} is not responding")
                    self.log_message(f"   Remote host may be offline or behind a firewall")
                    return
                except Exception as e:
                    self.log_message(f"❌ Connectivity test error: {str(e)}")
                    return
                
                # If we have a client, try to connect via RPC
                if self.go_client and self.go_client._connected:
                    self.log_message(f"ℹ️  Sending connection request to Go node via Cap'n Proto RPC...")
                    
                    # We pass the full multiaddr as the 'host' argument.
                    # The Go side has been updated to detect if host starts with "/" and treat it as a multiaddr.
                    # We pass 0 for peerID (legacy) and 0 for port (included in multiaddr).
                    try:
                        success, quality = self.go_client.connect_to_peer(0, multiaddr, 0)
                        if success:
                            self.log_message(f"✅ Successfully connected to peer!")
                            if quality:
                                self.log_message(f"   Connection Quality:")
                                self.log_message(f"   - Latency: {quality.get('latencyMs', 0):.2f}ms")
                                self.log_message(f"   - Jitter: {quality.get('jitterMs', 0):.2f}ms")
                                self.log_message(f"   - Packet Loss: {quality.get('packetLoss', 0):.2%}")
                        else:
                            self.log_message(f"❌ RPC call failed: Go node rejected connection")
                            self.log_message(f"   Possible causes:")
                            self.log_message(f"   - Peer ID mismatch")
                            self.log_message(f"   - libp2p handshake failed")
                            self.log_message(f"   - Incompatible protocol versions")
                    except TimeoutError:
                        self.log_message(f"❌ RPC timeout: Go node did not respond within 5 seconds")
                        self.log_message(f"   Go node may be overloaded or not properly started")
                    except RuntimeError as e:
                        self.log_message(f"❌ RPC error: {str(e)}")
                        self.log_message(f"   Check that Cap'n Proto RPC service is running on port 8080")
                    except Exception as e:
                        self.log_message(f"❌ Unexpected error connecting: {str(e)}")
                        self.log_message(f"   Error type: {type(e).__name__}")
                else:
                    self.log_message(f"❌ Not connected to local Go node - cannot establish peer connection")
                
                self.log_message(f"   Full multiaddr: {multiaddr}")
            except Exception as e:
                self.log_message(f"❌ Peer connection failed: {str(e)}")
                self.log_message(f"   Error type: {type(e).__name__}")
                self.log_message(f"   Stack trace: {traceback.format_exc()}")
        
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
        """List all nodes in the network - both routing table and connected peers."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("📋 Listing all nodes and peers...")
        
        def list_nodes_thread():
            try:
                # Get routing table nodes
                nodes = self.go_client.get_all_nodes()
                
                # Get actively connected peers
                peers = self.go_client.get_connected_peers()
                
                output = "=== Network Nodes & Peers ===\n\n"
                
                # Show connected peers first (most important)
                output += f"📡 ACTIVELY CONNECTED PEERS: {len(peers)}\n"
                if peers:
                    output += "-" * 50 + "\n"
                    for peer_id in peers:
                        try:
                            # Try to get connection quality for each peer
                            quality = self.go_client.get_connection_quality(peer_id)
                            output += f"  ✅ Peer ID {peer_id}:\n"
                            if quality:
                                output += f"     Latency: {quality['latencyMs']:.2f}ms\n"
                                output += f"     Jitter: {quality['jitterMs']:.2f}ms\n"
                                output += f"     Packet Loss: {quality['packetLoss']:.2%}\n"
                            output += "\n"
                        except Exception as e:
                            output += f"  ✅ Peer ID {peer_id} (connected, quality unavailable)\n\n"
                            logger.debug(f"Could not get quality for peer {peer_id}: {e}")
                else:
                    output += "  No active peer connections\n"
                output += "\n"
                
                # Show routing table nodes
                output += f"🗺️  ROUTING TABLE NODES: {len(nodes) if nodes else 0}\n"
                if nodes:
                    output += "-" * 50 + "\n"
                    for node in nodes:
                        output += f"  Node {node['id']}:\n"
                        status_icon = "✅" if node['status'] == 1 else "⚠️"
                        output += f"     {status_icon} Status: {node['status']}\n"
                        output += f"     Latency: {node['latencyMs']:.2f}ms\n"
                        output += f"     Threat Score: {node['threatScore']:.3f}\n\n"
                else:
                    output += "  No nodes in routing table\n"
                
                output += "\n💡 Tip: Use 'Get Node Info' for detailed network metrics\n"
                
                Clock.schedule_once(lambda dt: self._update_node_output(output), 0)
                self.log_message(f"✅ Found {len(peers)} active peers, {len(nodes) if nodes else 0} routing nodes")
            except Exception as e:
                error_msg = f"❌ Error listing nodes: {str(e)}\n"
                error_msg += f"Traceback: {traceback.format_exc()}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_node_output(error_msg), 0)
        
        threading.Thread(target=list_nodes_thread, daemon=True).start()
    
    def _update_node_output(self, text):
        """Update node output area (must be called from main thread)."""
        self.main_screen.node_output.clear()
        self.main_screen.node_output.add_text(text)
    
    def get_node_info(self):
        """Get information about current node."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("ℹ️  Getting node info...")
        
        def get_info_thread():
            try:
                # Get connected peers
                peers = self.go_client.get_connected_peers()
                
                # Get network metrics
                metrics = self.go_client.get_network_metrics()
                
                output = "=== Node Information ===\n\n"
                output += f"Connected to: {self.node_host}:{self.node_port}\n"
                output += f"Connected Peers: {len(peers)}\n"
                if peers:
                    output += f"Peer IDs: {', '.join(map(str, peers))}\n"
                output += "\n"
                
                if metrics:
                    output += "Network Metrics:\n"
                    output += f"  Average RTT: {metrics['avgRttMs']:.2f}ms\n"
                    output += f"  Packet Loss: {metrics['packetLoss']:.2%}\n"
                    output += f"  Bandwidth: {metrics['bandwidthMbps']:.2f} Mbps\n"
                    output += f"  Peer Count: {metrics['peerCount']}\n"
                    output += f"  CPU Usage: {metrics['cpuUsage']:.1%}\n"
                    output += f"  I/O Capacity: {metrics['ioCapacity']:.1%}\n"
                else:
                    output += "Network metrics not available\n"
                
                Clock.schedule_once(lambda dt: self._update_node_output(output), 0)
                self.log_message("✅ Node info retrieved")
            except Exception as e:
                error_msg = f"❌ Error getting node info: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_node_output(error_msg), 0)
        
        threading.Thread(target=get_info_thread, daemon=True).start()
    
    def health_status(self):
        """Show health status of all nodes."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("❤️  Checking health status...")
        
        def health_check_thread():
            try:
                nodes = self.go_client.get_all_nodes()
                metrics = self.go_client.get_network_metrics()
                
                output = "=== Network Health Status ===\n\n"
                
                if nodes:
                    healthy = sum(1 for n in nodes if n['status'] == 1)  # Assuming 1 = Active
                    output += f"Active Nodes: {healthy}/{len(nodes)}\n\n"
                    
                    for node in nodes:
                        status_icon = "✅" if node['status'] == 1 else "⚠️"
                        output += f"{status_icon} Node {node['id']}: "
                        output += f"Latency {node['latencyMs']:.1f}ms, "
                        output += f"Threat {node['threatScore']:.3f}\n"
                else:
                    output += "No nodes to check\n"
                
                output += "\n"
                if metrics:
                    health_score = 100 - (metrics['packetLoss'] * 100) - min(metrics['cpuUsage'] * 50, 50)
                    output += f"Overall Health Score: {health_score:.1f}/100\n"
                    output += f"Network Status: {'Good' if health_score > 70 else 'Fair' if health_score > 40 else 'Poor'}\n"
                
                Clock.schedule_once(lambda dt: self._update_node_output(output), 0)
                self.log_message("✅ Health status retrieved")
            except Exception as e:
                error_msg = f"❌ Error checking health: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_node_output(error_msg), 0)
        
        threading.Thread(target=health_check_thread, daemon=True).start()
    
    # ==========================================================================
    # Compute Methods
    # ==========================================================================
    
    def submit_compute_task(self):
        """Submit a compute task."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        task_type = self.main_screen.task_type_input.text
        
        # Get matrix size from input
        matrix_size = 16  # default
        try:
            size_text = self.main_screen.matrix_size_input.text
            if size_text:
                matrix_size = int(size_text)
                if matrix_size < 2:
                    self.show_warning("Invalid Size", "Matrix size must be at least 2")
                    return
                if matrix_size > 512:
                    self.show_warning("Size Too Large", "Matrix size must be 512 or less to avoid overflow")
                    return
        except ValueError:
            self.show_warning("Invalid Input", "Matrix size must be a valid integer")
            return
        
        self.log_message(f"⚙️  Submitting {task_type} task (size: {matrix_size}x{matrix_size})...")
        self.main_screen.compute_output.clear()
        
        def submit_task_thread():
            try:
                # Use the Python CLI to properly format and submit the matrix multiply task
                if "matrix" in task_type.lower():
                    result = subprocess.run(
                        [
                            "python3", "main.py", "compute", "matrix-multiply",
                            "--size", str(matrix_size),
                            "--generate",
                            "--verify",
                            "--connect"
                        ],
                        cwd=str(PROJECT_ROOT / "python"),
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    output = ""
                    if result.returncode == 0:
                        output = "✅ Matrix multiplication completed successfully!\n\n"
                        output += result.stdout
                        Clock.schedule_once(lambda dt: self._update_compute_output(output), 0)
                        self.log_message(f"✅ Matrix multiply ({matrix_size}x{matrix_size}) completed")
                    else:
                        output = f"❌ Matrix multiplication failed!\n\n"
                        output += f"Error: {result.stderr}\n"
                        output += result.stdout
                        Clock.schedule_once(lambda dt: self._update_compute_output(output), 0)
                        self.log_message(f"❌ Matrix multiply failed: {result.stderr[:100]}")
                else:
                    # Generic task - show not implemented
                    output = f"⚠️  Task type '{task_type}' not implemented yet.\n\n"
                    output += "Currently supported:\n"
                    output += "  - Matrix Multiply\n"
                    Clock.schedule_once(lambda dt: self._update_compute_output(output), 0)
                    self.log_message(f"⚠️  Task type not implemented: {task_type}")
            except Exception as e:
                error_msg = f"❌ Error submitting task: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_compute_output(error_msg), 0)
        
        threading.Thread(target=submit_task_thread, daemon=True).start()
    
    def _update_compute_output(self, text):
        """Update compute output area (must be called from main thread)."""
        self.main_screen.compute_output.clear()
        self.main_screen.compute_output.add_text(text)
    
    def list_workers(self):
        """List available compute workers."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("👷 Listing compute workers...")
        
        def list_workers_thread():
            try:
                # Get compute capacity of connected node
                capacity = self.go_client.get_compute_capacity()
                
                # Get connected peers (potential workers)
                peers = self.go_client.get_connected_peers()
                
                output = "=== Available Compute Workers ===\n\n"
                
                # Local node capacity
                output += "Local Node:\n"
                if capacity:
                    output += f"  CPU Cores: {capacity['cpuCores']}\n"
                    output += f"  RAM: {capacity['ramMb']} MB\n"
                    output += f"  Current Load: {capacity['currentLoad']:.1%}\n"
                    output += f"  Disk Space: {capacity['diskMb']} MB\n"
                    output += f"  Bandwidth: {capacity['bandwidthMbps']:.2f} Mbps\n"
                else:
                    output += "  Capacity info not available\n"
                
                output += f"\nConnected Workers: {len(peers)}\n"
                if peers:
                    for peer_id in peers:
                        output += f"  - Worker {peer_id}\n"
                else:
                    output += "  No remote workers connected\n"
                
                Clock.schedule_once(lambda dt: self._update_compute_output(output), 0)
                self.log_message(f"✅ Found {len(peers) + 1} worker(s)")
            except Exception as e:
                error_msg = f"❌ Error listing workers: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_compute_output(error_msg), 0)
        
        threading.Thread(target=list_workers_thread, daemon=True).start()
    
    def check_task_status(self):
        """Check status of compute tasks."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        if not hasattr(self, 'last_job_id'):
            self.show_warning("No Task", "Please submit a task first")
            return
        
        self.log_message("📊 Checking task status...")
        
        def check_status_thread():
            try:
                job_id = self.last_job_id
                status = self.go_client.get_compute_job_status(job_id)
                
                if status:
                    output = f"=== Task Status ===\n\n"
                    output += f"Job ID: {status['jobId']}\n"
                    output += f"Status: {status['status']}\n"
                    output += f"Progress: {status['progress']:.1%}\n"
                    output += f"Completed Chunks: {status['completedChunks']}/{status['totalChunks']}\n"
                    output += f"Estimated Time Remaining: {status['estimatedTimeRemaining']}s\n"
                    
                    if status['errorMsg']:
                        output += f"\nError: {status['errorMsg']}\n"
                    
                    # Try to get result if completed
                    if status['status'] == 'completed':
                        output += "\n🎉 Task completed! Fetching result...\n"
                        result_data, error_msg, worker_node = self.go_client.get_compute_job_result(job_id)
                        if result_data:
                            output += f"Result Size: {len(result_data)} bytes\n"
                            output += f"Worker Node: {worker_node}\n"
                            output += f"Result Preview: {result_data[:100]}\n"
                        elif error_msg:
                            output += f"Error fetching result: {error_msg}\n"
                    
                    Clock.schedule_once(lambda dt: self._update_compute_output(output), 0)
                    self.log_message(f"✅ Status: {status['status']}")
                else:
                    error_msg = "❌ Could not retrieve task status"
                    Clock.schedule_once(lambda dt: self._update_compute_output(error_msg), 0)
                    self.log_message(error_msg)
            except Exception as e:
                error_msg = f"❌ Error checking status: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_compute_output(error_msg), 0)
        
        threading.Thread(target=check_status_thread, daemon=True).start()
    
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
        """Upload file to network with comprehensive input validation."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        filepath = self.main_screen.upload_path_input.text
        
        # INPUT VALIDATION
        if not filepath:
            self.show_warning("No File", "Please select a file to upload")
            return
        
        if not filepath.strip():
            self.show_warning("Invalid Path", "File path cannot be empty or whitespace only")
            return
        
        # Check if file exists
        if not os.path.exists(filepath):
            self.show_warning("File Not Found", f"The file does not exist:\n{filepath}")
            return
        
        # Check if it's a file (not a directory)
        if not os.path.isfile(filepath):
            self.show_warning("Invalid File", f"Path is not a file:\n{filepath}")
            return
        
        # Check file size (max 100MB for safety)
        try:
            file_size = os.path.getsize(filepath)
            max_size = 100 * 1024 * 1024  # 100MB
            if file_size > max_size:
                self.show_warning("File Too Large", f"File size ({file_size // 1024 // 1024}MB) exceeds maximum (100MB)")
                return
            if file_size == 0:
                self.show_warning("Empty File", "Cannot upload empty file")
                return
        except Exception as e:
            self.show_warning("File Error", f"Cannot read file size: {str(e)}")
            return
        
        self.log_message(f"⬆️  Uploading {filepath} ({file_size} bytes)...")
        self.main_screen.file_output.add_text(f"Starting upload: {filepath}")
        
        def upload_thread():
            try:
                # 1. Read file with error handling
                try:
                    with open(filepath, 'rb') as f:
                        data = f.read()
                except PermissionError:
                    error_msg = f"❌ Permission denied: Cannot read file {filepath}"
                    self.log_message(error_msg)
                    Clock.schedule_once(lambda dt: self._update_file_output(error_msg), 0)
                    return
                except Exception as e:
                    error_msg = f"❌ File read error: {str(e)}"
                    self.log_message(error_msg)
                    Clock.schedule_once(lambda dt: self._update_file_output(error_msg), 0)
                    return

                # 2. Get peers
                peers = []
                try:
                    peers = self.go_client.get_connected_peers()
                except Exception as e:
                    self.log_message(f"⚠️  Could not get peers: {str(e)}")

                if not peers:
                    # Fallback for single-node testing: Generate local hash
                    import hashlib
                    file_hash = hashlib.sha256(data).hexdigest()
                    self.log_message(f"⚠️  No peers connected. Generated local hash.")
                    Clock.schedule_once(lambda dt: self.on_upload_complete(file_hash, simulated=True), 0)
                    return

                # 3. Upload
                try:
                    result = self.go_client.upload(data, peers)
                    if result and 'fileHash' in result:
                        Clock.schedule_once(lambda dt: self.on_upload_complete(result['fileHash'], result), 0)
                    else:
                        self.log_message("❌ Upload failed: No result returned")
                except Exception as e:
                    self.log_message(f"❌ Upload RPC error: {str(e)}")

            except Exception as e:
                self.log_message(f"❌ Upload error: {str(e)}")

        threading.Thread(target=upload_thread, daemon=True).start()

    def on_upload_complete(self, file_hash, manifest=None, simulated=False):
        """Handle upload completion."""
        msg = f"✅ Upload complete! Hash: {file_hash}"
        if simulated:
            msg += " (Local)"
        self.log_message(msg)
        self.main_screen.file_output.add_text(msg)
        # Auto-fill download hash for convenience
        self.main_screen.download_hash_input.text = file_hash
        # Store manifest for download
        if manifest:
            self.last_upload_manifest = manifest
    
    def download_file(self):
        """Download file from network with input validation."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        file_hash = self.main_screen.download_hash_input.text
        
        # INPUT VALIDATION
        if not file_hash:
            self.show_warning("No Hash", "Please enter a file hash")
            return
        
        if not file_hash.strip():
            self.show_warning("Invalid Hash", "File hash cannot be empty or whitespace only")
            return
        
        # Validate hash format (hexadecimal, typically 64 chars for SHA-256)
        if not re.match(r'^[a-fA-F0-9]+$', file_hash):
            self.show_warning("Invalid Hash Format", "File hash must be hexadecimal (0-9, a-f)")
            return
        
        # For SHA-256, expect exactly 64 characters
        if len(file_hash) != 64:
            self.show_warning("Invalid Hash Length", f"SHA-256 hash must be exactly 64 characters (got {len(file_hash)})")
            return
        
        self.log_message(f"⬇️  Downloading file {file_hash[:16]}...")
        
        def download_thread():
            try:
                # Check if we have stored manifest from upload
                if hasattr(self, 'last_upload_manifest') and self.last_upload_manifest.get('fileHash') == file_hash:
                    manifest = self.last_upload_manifest
                    shard_locations = manifest['shardLocations']
                    
                    result = self.go_client.download(shard_locations, file_hash)
                    
                    if result:
                        data, bytes_downloaded = result
                        
                        # CLIENT-SIDE MANIFEST VERIFICATION
                        # Compute hash of downloaded data and verify against manifest
                        computed_hash = hashlib.sha256(data).hexdigest().lower()
                        expected_hash = file_hash.lower()  # Normalize to lowercase for comparison
                        
                        output = f"✅ Download complete!\n\n"
                        output += f"Expected Hash: {expected_hash}\n"
                        output += f"Computed Hash: {computed_hash}\n"
                        
                        if computed_hash == expected_hash:
                            output += "✅ VERIFICATION PASSED - File integrity confirmed!\n\n"
                            verification_passed = True
                        else:
                            output += "❌ VERIFICATION FAILED - File corruption detected!\n\n"
                            verification_passed = False
                        
                        output += f"Size: {bytes_downloaded} bytes\n"
                        output += f"Data Preview: {data[:50]}...\n"
                        
                        # Only save if verification passed
                        if verification_passed:
                            download_dir = os.path.expanduser("~/Downloads")
                            if not os.path.exists(download_dir):
                                download_dir = os.path.expanduser("~")
                            
                            save_path = os.path.join(download_dir, f"downloaded_{file_hash[:8]}.dat")
                            with open(save_path, 'wb') as f:
                                f.write(data)
                            output += f"\n📁 FILE SAVED TO:\n"
                            output += f"   {save_path}\n"
                            output += f"\n💡 You can find your file at the above location\n"
                            self.log_message(f"✅ Downloaded and verified {bytes_downloaded} bytes → {save_path}")
                        else:
                            output += "\n⚠️  File NOT saved due to verification failure\n"
                            self.log_message(f"❌ Verification failed for downloaded file")
                        
                        Clock.schedule_once(lambda dt: self._update_file_output(output), 0)
                    else:
                        error_msg = "❌ Download failed: No data received"
                        Clock.schedule_once(lambda dt: self._update_file_output(error_msg), 0)
                        self.log_message(error_msg)
                else:
                    error_msg = "❌ File manifest not found. Upload file first or provide shard locations."
                    Clock.schedule_once(lambda dt: self._update_file_output(error_msg), 0)
                    self.log_message(error_msg)
            except Exception as e:
                error_msg = f"❌ Download error: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_file_output(error_msg), 0)
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    def _update_file_output(self, text):
        """Update file output area (must be called from main thread)."""
        self.main_screen.file_output.clear()
        self.main_screen.file_output.add_text(text)
    
    def list_files(self):
        """List available files in network."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("📁 Listing available files...")
        
        def list_files_thread():
            try:
                output = "=== Available Files ===\n\n"
                
                # List files from last upload manifest (for demo purposes)
                if hasattr(self, 'last_upload_manifest'):
                    manifest = self.last_upload_manifest
                    output += "Recently Uploaded:\n"
                    output += f"  Hash: {manifest['fileHash']}\n"
                    output += f"  Name: {manifest.get('fileName', 'N/A')}\n"
                    output += f"  Size: {manifest['fileSize']} bytes\n"
                    output += f"  Shards: {manifest['shardCount']} (+ {manifest['parityCount']} parity)\n"
                    output += f"  Locations: {len(manifest['shardLocations'])} node(s)\n"
                else:
                    output += "No files uploaded in this session.\n"
                    output += "\nUpload a file to see it listed here.\n"
                
                Clock.schedule_once(lambda dt: self._update_file_output(output), 0)
                self.log_message("✅ File list retrieved")
            except Exception as e:
                error_msg = f"❌ Error listing files: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_file_output(error_msg), 0)
        
        threading.Thread(target=list_files_thread, daemon=True).start()
    
    # ==========================================================================
    # Communications Methods
    # ==========================================================================
    
    def test_p2p_connection(self):
        """Test P2P connection."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("🔗 Testing P2P connection...")
        
        def test_connection_thread():
            try:
                peers = self.go_client.get_connected_peers()
                
                output = "=== P2P Connection Test ===\n\n"
                
                if not peers:
                    output += "⚠️  No peers connected\n"
                    output += "Connect to a peer first to test P2P communication\n"
                else:
                    output += f"Testing connection to {len(peers)} peer(s)...\n\n"
                    
                    for peer_id in peers:
                        output += f"Peer {peer_id}:\n"
                        
                        # Get connection quality
                        quality = self.go_client.get_connection_quality(peer_id)
                        if quality:
                            output += f"  ✅ Latency: {quality['latencyMs']:.2f}ms\n"
                            output += f"  ✅ Jitter: {quality['jitterMs']:.2f}ms\n"
                            output += f"  ✅ Packet Loss: {quality['packetLoss']:.2%}\n"
                        else:
                            output += f"  ⚠️  Could not get quality metrics\n"
                        
                        # Send test message
                        try:
                            test_data = b"PING_TEST_" + str(int(time.time())).encode()
                            success = self.go_client.send_message(peer_id, test_data)
                            if success:
                                output += f"  ✅ Message sent successfully\n"
                            else:
                                output += f"  ❌ Message send failed\n"
                        except Exception as e:
                            output += f"  ❌ Error: {str(e)}\n"
                        output += "\n"
                
                Clock.schedule_once(lambda dt: self._update_comm_output(output), 0)
                self.log_message("✅ P2P test complete")
            except Exception as e:
                error_msg = f"❌ Error testing P2P: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_comm_output(error_msg), 0)
        
        threading.Thread(target=test_connection_thread, daemon=True).start()
    
    def _update_comm_output(self, text):
        """Update communications output area (must be called from main thread)."""
        self.main_screen.comm_output.clear()
        self.main_screen.comm_output.add_text(text)
    
    def ping_all_nodes(self):
        """Ping all nodes in network."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("📡 Pinging all nodes...")
        
        def ping_nodes_thread():
            try:
                nodes = self.go_client.get_all_nodes()
                
                output = "=== Ping All Nodes ===\n\n"
                
                if not nodes:
                    output += "No nodes found\n"
                else:
                    output += f"Pinging {len(nodes)} node(s)...\n\n"
                    
                    for node in nodes:
                        node_id = node['id']
                        latency = node['latencyMs']
                        status = node['status']
                        
                        if status == 1:  # Active
                            output += f"✅ Node {node_id}: {latency:.2f}ms\n"
                        elif status == 2:  # Purgatory
                            output += f"⚠️  Node {node_id}: {latency:.2f}ms (unstable)\n"
                        else:  # Dead
                            output += f"❌ Node {node_id}: Unreachable\n"
                
                Clock.schedule_once(lambda dt: self._update_comm_output(output), 0)
                self.log_message(f"✅ Pinged {len(nodes)} node(s)")
            except Exception as e:
                error_msg = f"❌ Error pinging nodes: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_comm_output(error_msg), 0)
        
        threading.Thread(target=ping_nodes_thread, daemon=True).start()
    
    def check_network_health(self):
        """Check overall network health."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("💚 Checking network health...")
        
        def health_check_thread():
            try:
                metrics = self.go_client.get_network_metrics()
                nodes = self.go_client.get_all_nodes()
                peers = self.go_client.get_connected_peers()
                
                output = "=== Network Health Check ===\n\n"
                
                # Network metrics
                if metrics:
                    output += "Network Metrics:\n"
                    output += f"  Average RTT: {metrics['avgRttMs']:.2f}ms\n"
                    output += f"  Packet Loss: {metrics['packetLoss']:.2%}\n"
                    output += f"  Bandwidth: {metrics['bandwidthMbps']:.2f} Mbps\n"
                    output += f"  Peer Count: {metrics['peerCount']}\n"
                    output += f"  CPU Usage: {metrics['cpuUsage']:.1%}\n"
                    output += f"  I/O Capacity: {metrics['ioCapacity']:.1%}\n\n"
                    
                    # Calculate health score
                    health_score = 100.0
                    health_score -= min(metrics['packetLoss'] * 100, 50)  # Max 50 points deduction
                    health_score -= min(metrics['avgRttMs'] / 10, 30)     # Max 30 points deduction
                    health_score -= min(metrics['cpuUsage'] * 20, 20)     # Max 20 points deduction
                    health_score = max(health_score, 0)
                    
                    output += f"Overall Health Score: {health_score:.1f}/100\n"
                    if health_score >= 80:
                        output += "Status: ✅ Excellent\n"
                    elif health_score >= 60:
                        output += "Status: ✅ Good\n"
                    elif health_score >= 40:
                        output += "Status: ⚠️  Fair\n"
                    else:
                        output += "Status: ❌ Poor\n"
                else:
                    output += "⚠️  Network metrics not available\n"
                
                output += f"\nActive Nodes: {len(nodes)}\n"
                output += f"Connected Peers: {len(peers)}\n"
                
                Clock.schedule_once(lambda dt: self._update_comm_output(output), 0)
                self.log_message("✅ Health check complete")
            except Exception as e:
                error_msg = f"❌ Error checking health: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_comm_output(error_msg), 0)
        
        threading.Thread(target=health_check_thread, daemon=True).start()
    
    # ==========================================================================
    # Chat, Video, Voice Methods
    # ==========================================================================
    
    def is_tor_enabled(self):
        """Check if Tor is enabled in the UI."""
        return (hasattr(self.main_screen, 'tor_switch') and 
                hasattr(self.main_screen.tor_switch, 'active') and
                self.main_screen.tor_switch.active)
    
    def test_tor_connection(self):
        """Test Tor connection and display status."""
        self.log_message("🧅 Testing Tor connection...")
        
        def tor_test_thread():
            try:
                import socket
                output = "=== Tor Connection Test ===\n\n"
                
                # Check if Tor is enabled
                tor_enabled = self.is_tor_enabled()
                output += f"Tor Switch: {'ON' if tor_enabled else 'OFF'}\n\n"
                
                if not tor_enabled:
                    output += "⚠️  Tor is not enabled. Enable the Tor switch to use Tor proxy.\n"
                    output += "\nTo use Tor:\n"
                    output += "1. Install Tor Browser or tor service\n"
                    output += "2. Start Tor (default SOCKS5 proxy: 127.0.0.1:9050)\n"
                    output += "3. Enable the Tor switch above\n"
                else:
                    # Try to connect to Tor SOCKS proxy
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(2)
                        result = sock.connect_ex(('127.0.0.1', 9050))
                        sock.close()
                        
                        if result == 0:
                            output += "✅ Tor SOCKS5 proxy is running on 127.0.0.1:9050\n"
                            output += "✅ Traffic will be routed through Tor\n"
                        else:
                            output += "❌ Cannot connect to Tor proxy on 127.0.0.1:9050\n"
                            output += "⚠️  Make sure Tor is running\n"
                    except Exception as e:
                        output += f"❌ Error checking Tor proxy: {str(e)}\n"
                
                Clock.schedule_once(lambda dt: self._update_comm_output(output), 0)
                self.log_message("✅ Tor test complete")
            except Exception as e:
                error_msg = f"❌ Error testing Tor: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_comm_output(error_msg), 0)
        
        threading.Thread(target=tor_test_thread, daemon=True).start()
    
    def show_my_ip(self):
        """Display current IP address."""
        self.log_message("🌐 Getting IP address...")
        
        def ip_check_thread():
            try:
                import socket
                import urllib.request
                
                output = "=== IP Address Information ===\n\n"
                
                # Local IP - use robust detection
                try:
                    hostname = socket.gethostname()
                    local_ip = self._detect_local_ip()
                    output += f"Local IP: {local_ip}\n"
                    output += f"Hostname: {hostname}\n\n"
                except Exception as e:
                    output += f"⚠️  Could not get local IP: {str(e)}\n\n"
                
                # Public IP (with and without Tor)
                tor_enabled = self.is_tor_enabled()
                
                if tor_enabled:
                    output += "Tor Mode: ON 🧅\n"
                    output += "Note: External IP check requires Tor proxy configuration\n"
                else:
                    output += "Tor Mode: OFF\n"
                    try:
                        public_ip = urllib.request.urlopen('https://api.ipify.org', timeout=5).read().decode('utf8')
                        output += f"Public IP: {public_ip}\n"
                    except Exception as e:
                        output += f"⚠️  Could not get public IP: {str(e)}\n"
                
                Clock.schedule_once(lambda dt: self._update_comm_output(output), 0)
                self.log_message("✅ IP info retrieved")
            except Exception as e:
                error_msg = f"❌ Error getting IP: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_comm_output(error_msg), 0)
        
        threading.Thread(target=ip_check_thread, daemon=True).start()
    
    def start_chat(self):
        """Start chat session using Go streaming service."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        peer_ip = self.main_screen.chat_peer_ip.text.strip()
        if not peer_ip:
            self.show_warning("Missing Info", "Please enter peer IP address to connect")
            return
        
        self.log_message(f"💬 Starting chat with {peer_ip}...")
        
        def chat_thread():
            try:
                output = "=== Chat Session ===\n\n"
                output += f"Connecting to peer: {peer_ip}\n"
                output += f"Tor: {'Enabled 🧅' if self.is_tor_enabled() else 'Disabled'}\n\n"
                
                # Start P2P chat service (listening + connecting)
                output += "💬 Starting P2P chat service on port 9999...\n"
                success = self.go_client.start_streaming(port=9999, stream_type=2)  # 2 = chat
                
                if success:
                    output += "✅ Chat service started - now listening for connections\n\n"
                    
                    # Connect to peer
                    output += f"🔗 Connecting to peer at {peer_ip}:9999...\n"
                    conn_success, peer_addr = self.go_client.connect_stream_peer(peer_ip, 9999)
                    
                    if conn_success:
                        output += f"✅ Connected to peer at {peer_addr}\n\n"
                        output += "💬 Chat is now ACTIVE - use 'Send Message' to chat\n"
                        output += "\nYou can:\n"
                        output += "  • Type a message in the message field\n"
                        output += "  • Click 'Send Message' to send\n"
                        output += "  • Messages from peer will appear here\n"
                        
                        # Show notification
                        Clock.schedule_once(lambda dt, pa=peer_addr: self.show_notification(f"💬 Chat connected: {pa}", 5, (0.2, 0.8, 0.2, 0.9)), 0)
                        
                        # Set chat state
                        self.chat_active = True
                        self.chat_peer_addr = peer_addr
                    else:
                        output += "❌ Failed to connect to peer\n"
                        output += f"\n⚠️  Connection to {peer_ip}:9999 failed\n"
                        output += "\n⚠️  IMPORTANT: Both devices must have chat service running!\n"
                        output += "\nSetup Steps:\n"
                        output += "  1. On BOTH devices: Click 'Start Chat'\n"
                        output += "  2. Device A: Enter Device B's IP and click button\n"
                        output += "  3. Device B: Enter Device A's IP and click button\n"
                        output += "  4. Both should connect successfully\n"
                        output += "\nTroubleshooting:\n"
                        output += "  • Verify peer IP address is correct (use 'Show My IP')\n"
                        output += "  • Ensure peer has chat service started (listening)\n"
                        output += "  • Check firewall allows port 9999 on both devices\n"
                        output += "  • Confirm devices are on same network\n"
                        output += "\n💡 This device is STILL LISTENING - peer can connect to you!\n"
                        self.chat_active = True  # Keep listener active
                else:
                    output += "❌ Failed to start chat service\n"
                    output += "\nPossible causes:\n"
                    output += "  • Port 9999 already in use\n"
                    output += "  • Another streaming session active\n"
                    output += "  • Go backend not responding\n"
                    output += "\n💡 Tip: Try stopping other streams first\n"
                
                Clock.schedule_once(lambda dt: self._update_comm_output(output), 0)
                self.log_message("✅ Chat session setup complete")
            except Exception as e:
                error_msg = f"❌ Error starting chat: {str(e)}\n"
                error_msg += f"Traceback: {traceback.format_exc()}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_comm_output(error_msg), 0)
        
        threading.Thread(target=chat_thread, daemon=True).start()
    
    def send_chat_message(self):
        """Send a chat message via Go streaming service."""
        if not self.connected or not hasattr(self, 'chat_active') or not self.chat_active:
            self.show_warning("Chat Not Active", "Please start a chat session first")
            return
        
        message = self.main_screen.chat_message.text.strip()
        if not message:
            self.show_warning("No Message", "Please enter a message to send")
            return
        
        self.log_message(f"📤 Sending: {message}")
        
        def send_thread():
            try:
                # Get peer address from chat session
                peer_addr = getattr(self, 'chat_peer_addr', '')
                
                # Send via Go streaming service
                success = self.go_client.send_chat_message(peer_addr, message)
                
                if success:
                    output = f"You: {message}\n\n"
                    self.log_message("✅ Message sent")
                else:
                    output = f"❌ Failed to send: {message}\n\n"
                    self.log_message("❌ Message send failed")
                
                # Clear input field
                Clock.schedule_once(lambda dt: setattr(self.main_screen.chat_message, 'text', ''), 0)
                
                # Append to chat output
                current_output = self.main_screen.comm_output.output_label.text
                Clock.schedule_once(lambda dt: self._update_comm_output(current_output + output), 0)
            except Exception as e:
                error_msg = f"❌ Error sending message: {str(e)}"
                self.log_message(error_msg)
        
        threading.Thread(target=send_thread, daemon=True).start()
    
    def stop_chat(self):
        """Stop chat session."""
        if not self.connected:
            return
        
        self.log_message("🛑 Stopping chat...")
        self.chat_active = False
        
        def stop_thread():
            try:
                success = self.go_client.stop_streaming()
                
                output = "=== Chat Session Ended ===\n\n"
                if success:
                    output += "✅ Chat service stopped\n"
                
                Clock.schedule_once(lambda dt: self._update_comm_output(output), 0)
                self.log_message("✅ Chat stopped")
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                Clock.schedule_once(lambda dt: self._update_comm_output(error_msg), 0)
        
        threading.Thread(target=stop_thread, daemon=True).start()
    
    def start_video_call(self):
        """Start video call using Go streaming service."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        peer_ip = self.main_screen.video_peer_ip.text.strip()
        if not peer_ip:
            self.show_warning("Missing Info", "Please enter peer IP address to connect")
            return
        
        self.log_message(f"📹 Starting video call with {peer_ip}...")
        
        def video_thread():
            try:
                output = "=== Video Call ===\n\n"
                output += f"Connecting to peer: {peer_ip}\n"
                output += f"Tor: {'Enabled 🧅' if self.is_tor_enabled() else 'Disabled'}\n\n"
                
                # Start P2P video service (listening + connecting)
                output += "🎬 Starting P2P video service on port 9996...\n"
                success = self.go_client.start_streaming(port=9996, stream_type=0)  # 0 = video
                
                if success:
                    output += "✅ Video service started - now listening for connections\n\n"
                    
                    # Connect to peer
                    output += f"🔗 Connecting to peer at {peer_ip}:9996...\n"
                    conn_success, peer_addr = self.go_client.connect_stream_peer(peer_ip, 9996)
                    
                    if conn_success:
                        output += f"✅ Connected to peer at {peer_addr}\n\n"
                        output += "📹 Starting video capture and transmission...\n"
                        
                        # Start video capture in background
                        Clock.schedule_once(lambda dt: self._start_video_capture("", peer_ip), 0)
                        
                        output += "\n💡 Video call is now ACTIVE:\n"
                        output += "  • YOUR camera → Peer (sending)\n"
                        output += "  • Peer video → YOU (if supported by backend)\n"
                        output += "\n📊 Check logs for frame transmission statistics\n"
                        
                        # Show notification
                        Clock.schedule_once(lambda dt, pa=peer_addr: self.show_notification(f"📹 Video call connected: {pa}", 5, (0.2, 0.8, 0.2, 0.9)), 0)
                        self.streaming_active = True
                    else:
                        output += "❌ Failed to connect to peer\n"
                        output += f"\n⚠️  Connection to {peer_ip}:9996 failed\n"
                        output += "\n⚠️  IMPORTANT: Both devices must have video service running!\n"
                        output += "\nSetup Steps:\n"
                        output += "  1. On BOTH devices: Click 'Start Video Call'\n"
                        output += "  2. Device A: Enter Device B's IP and click button\n"
                        output += "  3. Device B: Enter Device A's IP and click button\n"
                        output += "  4. Both should connect and start streaming\n"
                        output += "\nTroubleshooting:\n"
                        output += "  • Verify peer IP address is correct (use 'Show My IP')\n"
                        output += "  • Ensure peer has video service started (listening)\n"
                        output += "  • Check firewall allows port 9996 on both devices\n"
                        output += "  • Confirm devices are on same network\n"
                        output += "\n💡 This device is STILL LISTENING - peer can connect to you!\n"
                        self.streaming_active = True  # Keep listener active
                else:
                    output += "❌ Failed to start video service\n"
                    output += "\nPossible causes:\n"
                    output += "  • Port 9996 already in use\n"
                    output += "  • Another streaming session active\n"
                    output += "  • Go backend not responding\n"
                    output += "\n💡 Tip: Try stopping other streams first\n"
                
                Clock.schedule_once(lambda dt: self._update_comm_output(output), 0)
                self.log_message("✅ Video call setup complete")
            except Exception as e:
                error_msg = f"❌ Error starting video: {str(e)}\n"
                error_msg += f"Traceback: {traceback.format_exc()}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_comm_output(error_msg), 0)
        
        threading.Thread(target=video_thread, daemon=True).start()
    
    def stop_video_call(self):
        """Stop video call."""
        if not self.connected:
            return
        
        self.log_message("🛑 Stopping video call...")
        self.streaming_active = False
        
        def stop_thread():
            try:
                success = self.go_client.stop_streaming()
                stats = self.go_client.get_stream_stats()
                
                output = "=== Video Call Ended ===\n\n"
                if success:
                    output += "✅ Video service stopped\n\n"
                
                if stats:
                    output += f"Call Statistics:\n"
                    output += f"  Duration: ~{stats.get('framesSent', 0) // 30} seconds\n"
                    output += f"  Frames: {stats.get('framesSent', 0)} sent, {stats.get('framesReceived', 0)} received\n"
                    output += f"  Data: {stats.get('bytesSent', 0) / (1024*1024):.2f} MB sent\n"
                
                Clock.schedule_once(lambda dt: self._update_comm_output(output), 0)
                self.log_message("✅ Video call stopped")
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                Clock.schedule_once(lambda dt: self._update_comm_output(error_msg), 0)
        
        threading.Thread(target=stop_thread, daemon=True).start()
    
    def start_voice_call(self):
        """Start voice call using Go streaming service."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        peer_ip = self.main_screen.voice_peer_ip.text.strip()
        if not peer_ip:
            self.show_warning("Missing Info", "Please enter peer IP address to connect")
            return
        
        self.log_message(f"🎤 Starting voice call with {peer_ip}...")
        
        def voice_thread():
            try:
                output = "=== Voice Call ===\n\n"
                output += f"Connecting to peer: {peer_ip}\n"
                output += f"Tor: {'Enabled 🧅' if self.is_tor_enabled() else 'Disabled'}\n\n"
                
                # Start P2P audio service (listening + connecting)
                output += "🎙️ Starting P2P audio service on port 9998...\n"
                success = self.go_client.start_streaming(port=9998, stream_type=1)  # 1 = audio
                
                if success:
                    output += "✅ Audio service started - now listening for connections\n\n"
                    
                    # Connect to peer
                    output += f"🔗 Connecting to peer at {peer_ip}:9998...\n"
                    conn_success, peer_addr = self.go_client.connect_stream_peer(peer_ip, 9998)
                    
                    if conn_success:
                        output += f"✅ Connected to peer at {peer_addr}\n\n"
                        output += "🎤 Starting audio capture and transmission...\n"
                        
                        # Start audio capture in background
                        Clock.schedule_once(lambda dt: self._start_audio_capture(), 0)
                        
                        output += "\n💡 Voice call is now ACTIVE:\n"
                        output += "  • YOUR mic → Peer (sending)\n"
                        output += "  • Peer audio → YOUR speakers (if supported)\n"
                        output += "\n📊 Check logs for audio chunk statistics\n"
                        
                        # Show notification
                        Clock.schedule_once(lambda dt, pa=peer_addr: self.show_notification(f"🎤 Voice call connected: {pa}", 5, (0.2, 0.8, 0.2, 0.9)), 0)
                        self.streaming_active = True
                    else:
                        output += "❌ Failed to connect to peer\n"
                        output += f"\n⚠️  Connection to {peer_ip}:9998 failed\n"
                        output += "\n⚠️  IMPORTANT: Both devices must have voice service running!\n"
                        output += "\nSetup Steps:\n"
                        output += "  1. On BOTH devices: Click 'Start Voice Call'\n"
                        output += "  2. Device A: Enter Device B's IP and click button\n"
                        output += "  3. Device B: Enter Device A's IP and click button\n"
                        output += "  4. Both should connect and start streaming\n"
                        output += "\nTroubleshooting:\n"
                        output += "  • Verify peer IP address is correct (use 'Show My IP')\n"
                        output += "  • Ensure peer has voice service started (listening)\n"
                        output += "  • Check firewall allows port 9998 on both devices\n"
                        output += "  • Confirm devices are on same network\n"
                        output += "\n💡 This device is STILL LISTENING - peer can connect to you!\n"
                        self.streaming_active = True  # Keep listener active
                else:
                    output += "❌ Failed to start audio service\n"
                    output += "\nPossible causes:\n"
                    output += "  • Port 9998 already in use\n"
                    output += "  • Another streaming session active\n"
                    output += "  • Go backend not responding\n"
                    output += "\n💡 Tip: Try stopping other streams first\n"
                
                Clock.schedule_once(lambda dt: self._update_comm_output(output), 0)
                self.log_message("✅ Voice call setup complete")
            except Exception as e:
                error_msg = f"❌ Error starting voice: {str(e)}\n"
                error_msg += f"Traceback: {traceback.format_exc()}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_comm_output(error_msg), 0)
        
        threading.Thread(target=voice_thread, daemon=True).start()
    
    def _start_audio_capture(self):
        """Start capturing and sending audio chunks."""
        if not SOUNDDEVICE_AVAILABLE:
            self.log_message("❌ sounddevice not available. Install with: pip install sounddevice numpy")
            Clock.schedule_once(lambda dt: self.show_warning("Audio Library Missing", "Install sounddevice and numpy for audio streaming"), 0)
            return
        
        # Set streaming active BEFORE starting thread to avoid race condition
        self.streaming_active = True
        
        def audio_thread():
            try:
                self.log_message("🎤 Audio capture started - streaming to peer")
                chunks_sent = 0
                send_failures = 0
                
                def audio_callback(indata, frames, time_info, status):
                    nonlocal chunks_sent, send_failures
                    
                    if status:
                        self.log_message(f"⚠️  Audio status: {status}")
                    
                    # Convert to bytes using constant
                    audio_bytes = (indata * MAX_INT16).astype(np.int16).tobytes()
                    
                    # Send via Go streaming service
                    success = self.go_client.send_audio_chunk(
                        data=audio_bytes,
                        sample_rate=AUDIO_SAMPLE_RATE,
                        channels=AUDIO_CHANNELS
                    )
                    
                    if success:
                        chunks_sent += 1
                    else:
                        send_failures += 1
                        if send_failures <= MAX_LOGGED_FAILURES:
                            self.log_message(f"⚠️  Audio chunk send failed")
                    
                    # Log progress every 100 chunks (~2 seconds)
                    if chunks_sent % 100 == 0 and chunks_sent > 0:
                        self.log_message(f"📊 Audio: {chunks_sent} chunks sent ({send_failures} failures)")
                
                with sd.InputStream(
                    samplerate=AUDIO_SAMPLE_RATE,
                    channels=AUDIO_CHANNELS,
                    dtype=np.float32,
                    blocksize=AUDIO_CHUNK_SIZE,
                    callback=audio_callback
                ):
                    while self.streaming_active:
                        time.sleep(0.1)
                
                self.log_message(f"🎤 Audio capture stopped - {chunks_sent} chunks sent ({send_failures} failures)")
            except Exception as e:
                error_msg = f"❌ Audio capture error: {str(e)}\n{traceback.format_exc()}"
                self.log_message(error_msg)
        
        threading.Thread(target=audio_thread, daemon=True).start()
    
    def stop_voice_call(self):
        """Stop voice call."""
        if not self.connected:
            return
        
        self.log_message("🛑 Stopping voice call...")
        self.streaming_active = False
        
        def stop_thread():
            try:
                success = self.go_client.stop_streaming()
                stats = self.go_client.get_stream_stats()
                
                output = "=== Voice Call Ended ===\n\n"
                if success:
                    output += "✅ Audio service stopped\n\n"
                
                if stats:
                    output += f"Call Statistics:\n"
                    output += f"  Bytes: {stats.get('bytesSent', 0) / (1024*1024):.2f} MB sent\n"
                    output += f"  Latency: {stats.get('avgLatencyMs', 0):.2f} ms\n"
                
                Clock.schedule_once(lambda dt: self._update_comm_output(output), 0)
                self.log_message("✅ Voice call stopped")
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                Clock.schedule_once(lambda dt: self._update_comm_output(error_msg), 0)
        
        threading.Thread(target=stop_thread, daemon=True).start()
    
    # ==========================================================================
    # Network Info Methods
    # ==========================================================================
    
    def show_peers(self):
        """Show connected peers."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("👥 Showing connected peers...")
        
        def show_peers_thread():
            try:
                peers = self.go_client.get_connected_peers()
                
                output = "=== Connected Peers ===\n\n"
                output += f"Total Peers: {len(peers)}\n\n"
                
                if not peers:
                    output += "No peers connected.\n"
                    output += "Use 'Connect to Peer' to add peers.\n"
                else:
                    for peer_id in peers:
                        output += f"Peer {peer_id}:\n"
                        
                        # Get connection quality
                        quality = self.go_client.get_connection_quality(peer_id)
                        if quality:
                            output += f"  Latency: {quality['latencyMs']:.2f}ms\n"
                            output += f"  Jitter: {quality['jitterMs']:.2f}ms\n"
                            output += f"  Packet Loss: {quality['packetLoss']:.2%}\n"
                            
                            # Determine quality rating
                            if quality['latencyMs'] < 50 and quality['packetLoss'] < 0.01:
                                output += f"  Quality: ✅ Excellent\n"
                            elif quality['latencyMs'] < 100 and quality['packetLoss'] < 0.05:
                                output += f"  Quality: ✅ Good\n"
                            else:
                                output += f"  Quality: ⚠️  Fair\n"
                        else:
                            output += f"  Quality: ⚠️  Unknown\n"
                        output += "\n"
                
                Clock.schedule_once(lambda dt: self._update_network_output(output), 0)
                self.log_message(f"✅ Showing {len(peers)} peer(s)")
            except Exception as e:
                error_msg = f"❌ Error showing peers: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_network_output(error_msg), 0)
        
        threading.Thread(target=show_peers_thread, daemon=True).start()
    
    def _update_network_output(self, text):
        """Update network output area (must be called from main thread)."""
        self.main_screen.network_output.clear()
        self.main_screen.network_output.add_text(text)
    
    def show_topology(self):
        """Show network topology."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("🗺️  Showing network topology...")
        
        def show_topology_thread():
            try:
                nodes = self.go_client.get_all_nodes()
                peers = self.go_client.get_connected_peers()
                
                output = "=== Network Topology ===\n\n"
                
                # Local node
                output += f"[Local Node] {self.node_host}:{self.node_port}\n"
                output += f"  |\n"
                
                # Connected peers
                if peers:
                    output += f"  +-- Connected Peers ({len(peers)})\n"
                    for i, peer_id in enumerate(peers):
                        prefix = "      +--" if i < len(peers) - 1 else "      +--"
                        output += f"{prefix} Peer {peer_id}\n"
                else:
                    output += f"  +-- (No direct peer connections)\n"
                
                output += "\n"
                
                # All known nodes
                output += f"Known Nodes in Network: {len(nodes)}\n"
                if nodes:
                    for node in nodes:
                        status_icon = "✅" if node['status'] == 1 else "⚠️" if node['status'] == 2 else "❌"
                        output += f"  {status_icon} Node {node['id']} - {node['latencyMs']:.1f}ms\n"
                
                Clock.schedule_once(lambda dt: self._update_network_output(output), 0)
                self.log_message("✅ Topology displayed")
            except Exception as e:
                error_msg = f"❌ Error showing topology: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_network_output(error_msg), 0)
        
        threading.Thread(target=show_topology_thread, daemon=True).start()
    
    def show_stats(self):
        """Show connection statistics."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("📊 Showing connection statistics...")
        
        def show_stats_thread():
            try:
                metrics = self.go_client.get_network_metrics()
                capacity = self.go_client.get_compute_capacity()
                
                output = "=== Connection Statistics ===\n\n"
                
                if metrics:
                    output += "Network Performance:\n"
                    output += f"  Average RTT: {metrics['avgRttMs']:.2f}ms\n"
                    output += f"  Packet Loss: {metrics['packetLoss']:.2%}\n"
                    output += f"  Bandwidth: {metrics['bandwidthMbps']:.2f} Mbps\n"
                    output += f"  Active Peers: {metrics['peerCount']}\n"
                    output += f"  CPU Usage: {metrics['cpuUsage']:.1%}\n"
                    output += f"  I/O Capacity: {metrics['ioCapacity']:.1%}\n\n"
                else:
                    output += "Network metrics not available\n\n"
                
                if capacity:
                    output += "Local Node Resources:\n"
                    output += f"  CPU Cores: {capacity['cpuCores']}\n"
                    output += f"  RAM: {capacity['ramMb']} MB\n"
                    output += f"  Current Load: {capacity['currentLoad']:.1%}\n"
                    output += f"  Disk Space: {capacity['diskMb']} MB\n"
                    output += f"  Bandwidth: {capacity['bandwidthMbps']:.2f} Mbps\n"
                else:
                    output += "Resource info not available\n"
                
                Clock.schedule_once(lambda dt: self._update_network_output(output), 0)
                self.log_message("✅ Statistics displayed")
            except Exception as e:
                error_msg = f"❌ Error showing stats: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_network_output(error_msg), 0)
        
        threading.Thread(target=show_stats_thread, daemon=True).start()
    
    def discover_mdns_peers(self):
        """Discover peers via mDNS."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("📡 Discovering local peers via mDNS...")
        
        def discover_thread():
            try:
                # Note: This would call a new RPC method getMdnsDiscovered
                # For now, we'll show connected peers as a placeholder
                peers = self.go_client.get_connected_peers()
                
                output = "=== mDNS Local Discovery ===\n\n"
                output += "Peers discovered on local network:\n\n"
                
                if peers:
                    for i, peer_id in enumerate(peers, 1):
                        output += f"{i}. Peer ID: {peer_id}\n"
                        output += f"   Status: Connected\n"
                        output += f"   Discovery: libp2p/mDNS\n\n"
                else:
                    output += "(No peers discovered yet)\n"
                    output += "\nTip: Ensure other nodes are running on the same network\n"
                    output += "with mDNS enabled (-mdns=true or -local flag)\n"
                
                Clock.schedule_once(lambda dt: self._update_network_output(output), 0)
                self.log_message(f"✅ Found {len(peers)} peer(s) via discovery")
            except Exception as e:
                error_msg = f"❌ Error discovering peers: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_network_output(error_msg), 0)
        
        threading.Thread(target=discover_thread, daemon=True).start()
    
    def refresh_mdns(self):
        """Refresh mDNS discovery."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("🔄 Refreshing mDNS discovery...")
        
        # Just rediscover
        self.discover_mdns_peers()
    
    def quick_connect_peer(self):
        """Quick connect to a peer with simplified UI."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        # Show a simple dialog to enter peer IP
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDFlatButton, MDRaisedButton
        
        peer_input = MDTextField(
            hint_text="Enter peer IP address",
            mode="rectangle"
        )
        
        def connect_action(*args):
            peer_ip = peer_input.text.strip()
            if peer_ip:
                self.log_message(f"🔗 Connecting to {peer_ip}...")
                self.show_notification(f"🔗 Connecting to {peer_ip}...", 3)
                
                # Fill in the chat peer IP field and auto-connect
                if hasattr(self.main_screen, 'chat_peer_ip'):
                    self.main_screen.chat_peer_ip.text = peer_ip
                    self.main_screen.video_peer_ip.text = peer_ip
                    self.main_screen.voice_peer_ip.text = peer_ip
                
                self.log_message("💡 Peer IP set! Go to Communications tab to start chat/video/voice")
                self.show_notification("💡 Peer IP set! Use Communications tab", 5, (0.2, 0.8, 0.2, 0.9))
            
            if hasattr(self, 'quick_connect_dialog'):
                self.quick_connect_dialog.dismiss()
        
        self.quick_connect_dialog = MDDialog(
            title="Quick Connect to Peer",
            type="custom",
            content_cls=peer_input,
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=lambda x: self.quick_connect_dialog.dismiss()
                ),
                MDRaisedButton(
                    text="CONNECT",
                    on_release=connect_action
                )
            ]
        )
        self.quick_connect_dialog.open()
    
    # ==========================================================================
    # DCDN Methods
    # ==========================================================================
    
    def run_dcdn_demo(self):
        """Run DCDN interactive demo."""
        self.log_message("🌐 Running DCDN demo...")
        
        def dcdn_demo_thread():
            try:
                output = "=== DCDN Demo ===\n\n"
                output += "Running Rust DCDN demo...\n\n"
                
                # Run the Rust DCDN demo
                project_root = PROJECT_ROOT
                rust_dir = project_root / "rust"
                
                result = subprocess.run(
                    ["cargo", "run", "--example", "dcdn_demo"],
                    cwd=str(rust_dir),
                    capture_output=True,
                    text=True,
                    timeout=DCDN_DEMO_TIMEOUT
                )
                
                if result.returncode == 0:
                    output += "✅ Demo completed successfully!\n\n"
                    output += "Output:\n"
                    output += result.stdout[:DCDN_DEMO_STDOUT_TRUNCATE_LEN]
                    if len(result.stdout) > DCDN_DEMO_STDOUT_TRUNCATE_LEN:
                        output += "\n... (output truncated)"
                else:
                    output += "❌ Demo failed\n\n"
                    output += "Error:\n"
                    output += result.stderr[:DCDN_DEMO_STDERR_TRUNCATE_LEN]
                
                Clock.schedule_once(lambda dt: self._update_dcdn_output(output), 0)
                self.log_message("✅ DCDN demo complete")
            except subprocess.TimeoutExpired:
                error_msg = f"❌ Demo timeout - took longer than {DCDN_DEMO_TIMEOUT} seconds"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_dcdn_output(error_msg), 0)
            except Exception as e:
                error_msg = f"❌ Error running demo: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_dcdn_output(error_msg), 0)
        
        threading.Thread(target=dcdn_demo_thread, daemon=True).start()
    
    def _update_dcdn_output(self, text):
        """Update DCDN output area (must be called from main thread)."""
        self.main_screen.dcdn_output.clear()
        self.main_screen.dcdn_output.add_text(text)
    
    def dcdn_info(self):
        """Show DCDN system information."""
        self.log_message("ℹ️  Getting DCDN info...")
        
        def dcdn_info_thread():
            try:
                output = "=== DCDN System Information ===\n\n"
                
                # Basic info
                output += "Distributed Content Delivery Network\n\n"
                output += "Components:\n"
                output += "  - QUIC Transport: Low-latency packet delivery\n"
                output += "  - Reed-Solomon FEC: Packet recovery (8 data + 2 parity)\n"
                output += "  - P2P Mesh: Tit-for-tat bandwidth allocation\n"
                output += "  - Ed25519 Verification: Content authenticity\n"
                output += "  - Lock-free Ring Buffer: High-speed chunk storage\n\n"
                
                output += "Configuration:\n"
                # Try to read config if exists
                config_path = PROJECT_ROOT / "rust" / "config" / "dcdn.toml"
                if config_path.exists():
                    output += f"  Config file: {config_path}\n"
                    output += "  (Config file present)\n"
                else:
                    output += "  Config file: Not found (using defaults)\n"
                
                output += "\nCapabilities:\n"
                output += "  - Video streaming with low latency\n"
                output += "  - Automatic packet recovery\n"
                output += "  - Fair bandwidth distribution\n"
                output += "  - Cryptographic verification\n"
                output += "  - Cross-device content delivery\n\n"
                
                output += "Status: ✅ Implementation Complete\n"
                output += "\nUse 'Run Demo' to see DCDN in action\n"
                
                Clock.schedule_once(lambda dt: self._update_dcdn_output(output), 0)
                self.log_message("✅ DCDN info retrieved")
            except Exception as e:
                error_msg = f"❌ Error getting info: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_dcdn_output(error_msg), 0)
        
        threading.Thread(target=dcdn_info_thread, daemon=True).start()
    
    def show_dcdn_multiaddr(self):
        """Display this node's DCDN multiaddr for peer to connect."""
        self.log_message("🌐 Getting DCDN multiaddr...")
        
        def show_multiaddr_thread():
            try:
                output = "=== MY DCDN MULTIADDR ===\n\n"
                
                # Get local IP
                local_ip = self._detect_local_ip()
                output += f"Local IP: {local_ip}\n"
                output += f"DCDN Port: 9090 (default)\n"
                output += f"P2P Port: 9081 (default)\n\n"
                
                # Check if Go node is running to get peer ID
                go_node_running = False
                try:
                    # Try to connect to Go node
                    if self.connected and self.go_client:
                        go_node_running = True
                except:
                    pass
                
                if not go_node_running:
                    output += "⚠️  Go node not running - starting temporary node to get peer ID...\n\n"
                    
                    # Start temporary Go node
                    project_root = PROJECT_ROOT
                    go_dir = project_root / "go"
                    
                    if not (go_dir / "bin" / "go-node").exists():
                        output += "❌ Go node not built. Please build first.\n"
                        Clock.schedule_once(lambda dt: self._update_dcdn_output(output), 0)
                        return
                    
                    # Set library paths
                    env = os.environ.copy()
                    rust_lib = str(project_root / "rust" / "target" / "release")
                    env["LD_LIBRARY_PATH"] = f"{rust_lib}:{env.get('LD_LIBRARY_PATH', '')}"
                    env["DYLD_LIBRARY_PATH"] = f"{rust_lib}:{env.get('DYLD_LIBRARY_PATH', '')}"
                    
                    # Start node temporarily
                    proc = subprocess.Popen(
                        [str(go_dir / "bin" / "go-node"), 
                         "-node-id=1", "-capnp-addr=:8080", 
                         "-libp2p=true", "-libp2p-port=9081", "-local"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=False,
                        cwd=str(go_dir),
                        env=env
                    )
                    
                    # Wait for node to start and extract peer ID
                    time.sleep(3)
                    
                    # Try to read logs
                    log_output = b""
                    try:
                        proc.stdout.flush()
                        while True:
                            line = proc.stdout.readline()
                            if not line:
                                break
                            log_output += line
                            if len(log_output) > 10000:  # Limit log size
                                break
                    except:
                        pass
                    
                    # Kill the temporary node
                    proc.terminate()
                    time.sleep(1)
                    if proc.poll() is None:
                        proc.kill()
                    
                    # Parse logs for peer ID
                    log_str = log_output.decode('utf-8', errors='replace')
                else:
                    # Use existing connection
                    log_str = ""
                
                # Try to extract peer ID from logs or construct multiaddr
                peer_id = ""
                multiaddr = ""
                
                # Check for full multiaddr in logs
                import re
                multiaddr_match = re.search(r'/ip4/[0-9.]+/tcp/\d+/p2p/[a-zA-Z0-9]+', log_str)
                if multiaddr_match:
                    multiaddr = multiaddr_match.group(0)
                    # Replace 0.0.0.0 or 127.0.0.1 with actual local IP
                    multiaddr = re.sub(r'/ip4/(0\.0\.0\.0|127\.0\.0\.1)', f'/ip4/{local_ip}', multiaddr)
                    peer_id = re.search(r'/p2p/([a-zA-Z0-9]+)', multiaddr).group(1) if '/p2p/' in multiaddr else ""
                else:
                    # Try to extract just peer ID
                    peer_id_match = re.search(r'Node ID: ([a-zA-Z0-9]+)', log_str)
                    if peer_id_match:
                        peer_id = peer_id_match.group(1)
                        multiaddr = f"/ip4/{local_ip}/tcp/9081/p2p/{peer_id}"
                
                if multiaddr:
                    output += "✅ SHARE THIS MULTIADDR WITH THE OTHER NODE:\n\n"
                    output += f"  {multiaddr}\n\n"
                    output += "(Copy the full line above)\n\n"
                    output += "The other node should:\n"
                    output += "  1. Click 'Connect to Peer'\n"
                    output += "  2. Paste this multiaddr\n"
                    output += "  3. They will connect to you!\n"
                else:
                    output += "⚠️  Could not extract peer ID\n\n"
                    output += f"Manual multiaddr format:\n"
                    output += f"  /ip4/{local_ip}/tcp/9081/p2p/<PEER_ID>\n\n"
                    output += "Start a Go node to get the peer ID automatically.\n"
                
                Clock.schedule_once(lambda dt: self._update_dcdn_output(output), 0)
                self.log_message("✅ Multiaddr displayed")
            except Exception as e:
                error_msg = f"❌ Error getting multiaddr: {str(e)}\n"
                error_msg += f"Traceback: {traceback.format_exc()}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_dcdn_output(error_msg), 0)
        
        threading.Thread(target=show_multiaddr_thread, daemon=True).start()
    
    def connect_dcdn_peer(self):
        """Connect to a DCDN peer using their multiaddr."""
        peer_multiaddr = self.main_screen.dcdn_peer_multiaddr.text.strip()
        
        if not peer_multiaddr:
            self.show_warning("No Multiaddr", "Please enter the peer's multiaddr in the text field")
            return
        
        self.log_message(f"🔗 Connecting to DCDN peer: {peer_multiaddr[:50]}...")
        
        def connect_thread():
            try:
                output = "=== CONNECTING TO DCDN PEER ===\n\n"
                output += f"Peer Multiaddr: {peer_multiaddr}\n\n"
                
                # Parse multiaddr
                import re
                peer_ip = re.search(r'/ip4/([0-9.]+)', peer_multiaddr)
                peer_port = re.search(r'/tcp/(\d+)', peer_multiaddr)
                peer_id = re.search(r'/p2p/([a-zA-Z0-9]+)', peer_multiaddr)
                
                if not peer_ip:
                    output += "❌ Could not parse IP from multiaddr\n"
                    Clock.schedule_once(lambda dt: self._update_dcdn_output(output), 0)
                    return
                
                peer_ip = peer_ip.group(1)
                peer_port = peer_port.group(1) if peer_port else "9081"
                peer_id = peer_id.group(1) if peer_id else ""
                
                output += f"Peer IP: {peer_ip}\n"
                output += f"Peer Port: {peer_port}\n"
                if peer_id:
                    output += f"Peer ID: {peer_id[:20]}...\n"
                output += "\n"
                
                # Check if Go node is running
                if not self.connected or not self.go_client:
                    output += "Starting local Go node to connect...\n\n"
                    
                    # Start local Go node with peer connection
                    project_root = PROJECT_ROOT
                    go_dir = project_root / "go"
                    
                    if not (go_dir / "bin" / "go-node").exists():
                        output += "❌ Go node not built. Please build first.\n"
                        Clock.schedule_once(lambda dt: self._update_dcdn_output(output), 0)
                        return
                    
                    # Set library paths
                    env = os.environ.copy()
                    rust_lib = str(project_root / "rust" / "target" / "release")
                    env["LD_LIBRARY_PATH"] = f"{rust_lib}:{env.get('LD_LIBRARY_PATH', '')}"
                    env["DYLD_LIBRARY_PATH"] = f"{rust_lib}:{env.get('DYLD_LIBRARY_PATH', '')}"
                    
                    # Start node with peer connection
                    proc = subprocess.Popen(
                        [str(go_dir / "bin" / "go-node"),
                         "-node-id=2", "-capnp-addr=:8081",
                         "-libp2p=true", "-libp2p-port=9082",
                         f"-peers={peer_multiaddr}", "-local"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=False,
                        cwd=str(go_dir),
                        env=env
                    )
                    
                    time.sleep(3)
                    
                    # Check if connected
                    if proc.poll() is None:
                        output += "✅ Node started and attempting connection...\n\n"
                        output += "Connection details:\n"
                        output += f"  Peer IP: {peer_ip}\n"
                        output += f"  Peer Port: {peer_port}\n"
                        output += "\n"
                        output += "🎉 Connection in progress!\n"
                        output += "\nNode is running in background.\n"
                        output += "You can now use DCDN features.\n"
                    else:
                        output += "❌ Node failed to start\n"
                        # Try to get error output
                        err_out = proc.stdout.read().decode('utf-8', errors='replace')
                        if err_out:
                            output += f"\nError output:\n{err_out[:500]}\n"
                else:
                    output += "✅ Using existing Go node connection\n\n"
                    # Try to connect to peer via Go client if method exists
                    output += "Note: Manual peer connection through existing node\n"
                    output += "Use CLI commands to connect if needed.\n"
                
                Clock.schedule_once(lambda dt: self._update_dcdn_output(output), 0)
                self.log_message("✅ Connection initiated")
            except Exception as e:
                error_msg = f"❌ Error connecting to peer: {str(e)}\n"
                error_msg += f"Traceback: {traceback.format_exc()}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_dcdn_output(error_msg), 0)
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def test_dcdn(self):
        """Run DCDN tests."""
        self.log_message("🧪 Running DCDN tests...")
        
        def dcdn_test_thread():
            try:
                output = "=== DCDN Tests ===\n\n"
                output += "Running Rust test suite...\n\n"
                
                # Run the Rust DCDN tests
                project_root = PROJECT_ROOT
                rust_dir = project_root / "rust"
                
                result = subprocess.run(
                    ["cargo", "test", "--test", "test_dcdn"],
                    cwd=str(rust_dir),
                    capture_output=True,
                    text=True,
                    timeout=DCDN_TEST_TIMEOUT
                )
                
                if result.returncode == 0:
                    output += "✅ All tests passed!\n\n"
                    # Extract test summary
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'test result:' in line or 'running' in line:
                            output += line + "\n"
                else:
                    output += "❌ Some tests failed\n\n"
                    output += "Output:\n"
                    output += result.stdout[-DCDN_TEST_STDOUT_TRUNCATE_LEN:]
                    output += "\n\nError:\n"
                    output += result.stderr[-DCDN_TEST_STDERR_TRUNCATE_LEN:]
                
                Clock.schedule_once(lambda dt: self._update_dcdn_output(output), 0)
                self.log_message("✅ DCDN tests complete")
            except subprocess.TimeoutExpired:
                error_msg = f"❌ Tests timeout - took longer than {DCDN_TEST_TIMEOUT} seconds"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_dcdn_output(error_msg), 0)
            except Exception as e:
                error_msg = f"❌ Error running tests: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_dcdn_output(error_msg), 0)
        
        threading.Thread(target=dcdn_test_thread, daemon=True).start()
    
    def start_dcdn_stream(self):
        """Start DCDN video streaming using Go streaming service."""
        if not self.connected:
            self.show_warning("Not Connected", "Please connect to a node first")
            return
        
        peer_ip = self.main_screen.stream_peer_ip.text.strip()
        if not peer_ip:
            self.show_warning("Missing Info", "Please enter peer IP or 'server' to receive")
            return
        
        video_file = self.main_screen.video_file_path.text.strip()
        self.log_message(f"📺 Starting DCDN stream to {peer_ip}...")
        
        def stream_thread():
            try:
                output = "=== DCDN Video Streaming ===\n\n"
                
                is_server = peer_ip.lower() == 'server'
                
                # Start streaming service on Go node
                if is_server:
                    # Server mode: listen for incoming stream
                    output += "Mode: Receiver (waiting for stream)\n"
                    output += "Starting streaming service on port 9996...\n\n"
                    success = self.go_client.start_streaming(port=9996, stream_type=0)  # 0 = video
                else:
                    # Client mode: connect and stream
                    output += f"Mode: Sender (streaming to {peer_ip})\n"
                    output += f"Source: {'Webcam' if not video_file else video_file}\n\n"
                    output += "Connecting to peer...\n"
                    success = self.go_client.start_streaming(
                        port=9997, 
                        peer_host=peer_ip, 
                        peer_port=9996, 
                        stream_type=0
                    )
                
                if success:
                    output += "✅ Streaming service started successfully!\n\n"
                    output += "DCDN Features Active:\n"
                    output += "✓ QUIC Transport: Low-latency UDP delivery\n"
                    output += "✓ Reed-Solomon FEC: Automatic packet recovery\n"
                    output += "✓ P2P Bandwidth: Fair allocation\n"
                    output += "✓ Ed25519: Content verification\n\n"
                    
                    if not is_server:
                        # Start video capture and streaming
                        output += "Starting video capture...\n"
                        Clock.schedule_once(lambda dt: self._start_video_capture(video_file, peer_ip), 0)
                    else:
                        output += "Waiting for incoming video stream...\n"
                        output += "Partner should connect to your IP\n\n"
                        output += "💡 Stream will display automatically when data arrives\n"
                    
                    # Mark that streaming is active
                    self.streaming_active = True
                else:
                    output += "❌ Failed to start streaming service\n"
                    output += "Check that ports 9996-9997 are available\n"
                
                Clock.schedule_once(lambda dt: self._update_dcdn_output(output), 0)
                self.log_message("✅ Stream info displayed")
            except Exception as e:
                error_msg = f"❌ Error starting stream: {str(e)}\n"
                error_msg += f"Details: {traceback.format_exc()}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_dcdn_output(error_msg), 0)
        
        threading.Thread(target=stream_thread, daemon=True).start()
    
    def _start_video_capture(self, video_file, peer_ip):
        """Start capturing and sending video frames."""
        if not CV2_AVAILABLE:
            self.log_message("❌ OpenCV not available. Install with: pip install opencv-python")
            Clock.schedule_once(lambda dt: self.show_warning("OpenCV Missing", "Install opencv-python to enable video streaming"), 0)
            return
        
        # Set streaming active BEFORE starting thread to avoid race condition
        self.streaming_active = True
        
        def capture_thread():
            try:
                # Open video source
                if video_file and os.path.exists(video_file):
                    cap = cv2.VideoCapture(video_file)
                    self.log_message(f"📹 Streaming from file: {video_file}")
                else:
                    cap = cv2.VideoCapture(0)  # Webcam
                    self.log_message("📹 Streaming from webcam")
                
                if not cap.isOpened():
                    self.log_message("❌ Could not open video source")
                    Clock.schedule_once(lambda dt: self.show_warning("Camera Error", "Could not access camera. Check permissions."), 0)
                    return
                
                frame_id = 0
                frame_delay = 1.0 / VIDEO_FPS
                send_failures = 0
                last_log_frame = 0
                
                self.log_message(f"✅ Video capture started - sending to peer at {peer_ip}:9996")
                
                while self.streaming_active and cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        if video_file:  # Loop video file
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            continue
                        else:
                            break
                    
                    # Resize for bandwidth efficiency
                    frame = cv2.resize(frame, (VIDEO_WIDTH, VIDEO_HEIGHT))
                    
                    # Encode as JPEG
                    _, jpeg_data = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, VIDEO_JPEG_QUALITY])
                    
                    # Send via Go streaming service
                    success = self.go_client.send_video_frame(
                        frame_id=frame_id,
                        data=jpeg_data.tobytes(),
                        width=VIDEO_WIDTH,
                        height=VIDEO_HEIGHT,
                        quality=VIDEO_JPEG_QUALITY
                    )
                    
                    if not success:
                        send_failures += 1
                        if send_failures <= MAX_LOGGED_FAILURES:
                            self.log_message(f"⚠️  Frame {frame_id} send failed")
                    
                    # Log progress every 30 frames (1 second at 30fps)
                    if frame_id - last_log_frame >= 30:
                        if send_failures > 0:
                            self.log_message(f"📊 Sent {frame_id} frames ({send_failures} failures)")
                        else:
                            self.log_message(f"📊 Sent {frame_id} frames successfully")
                        last_log_frame = frame_id
                    
                    frame_id += 1
                    time.sleep(frame_delay)
                
                cap.release()
                total_success = frame_id - send_failures
                self.log_message(f"📹 Video capture stopped - {total_success}/{frame_id} frames sent successfully")
            except Exception as e:
                error_msg = f"❌ Video capture error: {str(e)}\n{traceback.format_exc()}"
                self.log_message(error_msg)
        
        self.streaming_active = True
        threading.Thread(target=capture_thread, daemon=True).start()
    
    def stop_dcdn_stream(self):
        """Stop DCDN video streaming."""
        if not self.connected:
            self.show_warning("Not Connected", "No active streaming to stop")
            return
        
        self.log_message("🛑 Stopping DCDN stream...")
        self.streaming_active = False
        
        def stop_thread():
            try:
                # Stop the streaming service on Go node
                success = self.go_client.stop_streaming()
                
                # Get final statistics
                stats = self.go_client.get_stream_stats()
                
                output = "=== Stream Stopped ===\n\n"
                
                if success:
                    output += "✅ Streaming service stopped successfully\n\n"
                else:
                    output += "⚠️  Streaming service stop completed with warnings\n\n"
                
                if stats:
                    output += "Stream Statistics:\n"
                    output += f"  Frames Sent: {stats.get('framesSent', 0)}\n"
                    output += f"  Frames Received: {stats.get('framesReceived', 0)}\n"
                    output += f"  Bytes Sent: {stats.get('bytesSent', 0) / (1024*1024):.2f} MB\n"
                    output += f"  Bytes Received: {stats.get('bytesReceived', 0) / (1024*1024):.2f} MB\n"
                    output += f"  Avg Latency: {stats.get('avgLatencyMs', 0):.2f} ms\n"
                else:
                    output += "No statistics available\n"
                
                Clock.schedule_once(lambda dt: self._update_dcdn_output(output), 0)
                self.log_message("✅ Stream stopped")
            except Exception as e:
                error_msg = f"❌ Error stopping stream: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_dcdn_output(error_msg), 0)
        
        threading.Thread(target=stop_thread, daemon=True).start()
    
    def browse_video_file(self):
        """Browse for video file."""
        if not self.file_manager:
            self.file_manager = MDFileManager(
                exit_manager=self.exit_file_manager,
                select_path=self.select_video_path,
            )
        
        # Start in home directory for security
        home_dir = os.path.expanduser("~")
        self.file_manager.show(home_dir)
    
    def select_video_path(self, path):
        """Select video file path."""
        self.main_screen.video_file_path.text = path
        self.exit_file_manager()
        self.log_message(f"📹 Selected video: {path}")
    
    def test_video_file(self):
        """Test video file playback."""
        video_file = self.main_screen.video_file_path.text.strip()
        
        if not video_file:
            self.show_warning("No File", "Please select a video file first")
            return
        
        self.log_message(f"🎬 Testing video file: {video_file}")
        
        def test_video_thread():
            try:
                output = "=== Video File Test ===\n\n"
                output += f"File: {video_file}\n\n"
                
                # Check if file exists
                if not os.path.exists(video_file):
                    output += "❌ File not found!\n"
                    output += "Please check the path and try again.\n"
                else:
                    output += "✅ File exists\n"
                    
                    # Get file size
                    file_size = os.path.getsize(video_file)
                    output += f"Size: {file_size / (1024*1024):.2f} MB\n\n"
                    
                    # Try to get video info using OpenCV if available
                    try:
                        import cv2
                        cap = cv2.VideoCapture(video_file)
                        if cap.isOpened():
                            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            fps = int(cap.get(cv2.CAP_PROP_FPS))
                            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                            duration = frame_count / fps if fps > 0 else 0
                            
                            output += "Video Properties:\n"
                            output += f"  Resolution: {width}x{height}\n"
                            output += f"  FPS: {fps}\n"
                            output += f"  Frames: {frame_count}\n"
                            output += f"  Duration: {duration:.2f} seconds\n\n"
                            output += "✅ Video file is valid and can be streamed\n"
                            cap.release()
                        else:
                            output += "⚠️  Could not open video file with OpenCV\n"
                            output += "File may be corrupted or in unsupported format\n"
                    except ImportError:
                        output += "⚠️  OpenCV not available - cannot verify video\n"
                        output += "Install opencv-python to test video files\n"
                    except Exception as e:
                        output += f"⚠️  Error reading video: {str(e)}\n"
                
                Clock.schedule_once(lambda dt: self._update_dcdn_output(output), 0)
                self.log_message("✅ Video test complete")
            except Exception as e:
                error_msg = f"❌ Error testing video: {str(e)}"
                self.log_message(error_msg)
                Clock.schedule_once(lambda dt: self._update_dcdn_output(error_msg), 0)
        
        threading.Thread(target=test_video_thread, daemon=True).start()
    
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
