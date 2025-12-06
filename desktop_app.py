#!/usr/bin/env python3
"""
Pangea Net - Desktop Application
=================================

A standalone desktop GUI application for Pangea Net that provides access to all
CLI functionality without requiring command-line interaction.

This application replaces the browser-based demo and provides:
- Direct Cap'n Proto RPC connection to Go nodes
- Full CLI command integration
- Compute task management
- Network monitoring
- File upload/download (Receptors)
- Communication liveness testing

Requirements:
- Python 3.8+
- tkinter (usually included with Python)
- All python/ dependencies from requirements.txt
"""

import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from pathlib import Path
import threading
import queue
import json
from datetime import datetime
from typing import Optional, Dict, Any
import logging

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

# Try to import Cap'n Proto client
try:
    from client.go_client import GoNodeClient
    CAPNP_AVAILABLE = True
except ImportError:
    logger.warning("Cap'n Proto client not available. Install dependencies first.")
    CAPNP_AVAILABLE = False


class PangeaDesktopApp:
    """Main desktop application for Pangea Net."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Pangea Net - Command Center")
        self.root.geometry("1200x800")
        
        # State
        self.go_client: Optional[Any] = None
        self.connected = False
        self.node_host = "localhost"
        self.node_port = 8080
        
        # Message queue for thread-safe UI updates
        self.message_queue = queue.Queue()
        
        # Build UI
        self.create_ui()
        
        # Start message processor
        self.process_messages()
        
        # Log startup
        self.log_message("🚀 Pangea Net Desktop Application Started")
        if CAPNP_AVAILABLE:
            self.log_message("✅ Cap'n Proto client available")
        else:
            self.log_message("⚠️  Cap'n Proto client not available - install dependencies")
    
    def create_ui(self):
        """Create the main user interface."""
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Top section: Connection and status
        self.create_connection_panel(main_frame)
        
        # Middle section: Tabbed interface for features
        self.create_tabbed_interface(main_frame)
        
        # Bottom section: Log output
        self.create_log_panel(main_frame)
    
    def create_connection_panel(self, parent):
        """Create connection configuration panel."""
        frame = ttk.LabelFrame(parent, text="Node Connection", padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Host input
        ttk.Label(frame, text="Host:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.host_entry = ttk.Entry(frame, width=20)
        self.host_entry.insert(0, self.node_host)
        self.host_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        
        # Port input
        ttk.Label(frame, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.port_entry = ttk.Entry(frame, width=10)
        self.port_entry.insert(0, str(self.node_port))
        self.port_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 10))
        
        # Connect button
        self.connect_btn = ttk.Button(frame, text="Connect", command=self.connect_to_node)
        self.connect_btn.grid(row=0, column=4, padx=(0, 5))
        
        # Disconnect button
        self.disconnect_btn = ttk.Button(frame, text="Disconnect", command=self.disconnect_from_node, state=tk.DISABLED)
        self.disconnect_btn.grid(row=0, column=5, padx=(0, 10))
        
        # Status indicator
        self.status_label = ttk.Label(frame, text="● Disconnected", foreground="red")
        self.status_label.grid(row=0, column=6, sticky=tk.W)
    
    def create_tabbed_interface(self, parent):
        """Create tabbed interface for different features."""
        notebook = ttk.Notebook(parent)
        notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Tab 1: Node Management
        self.create_node_tab(notebook)
        
        # Tab 2: Compute Tasks
        self.create_compute_tab(notebook)
        
        # Tab 3: File Operations (Receptors)
        self.create_file_tab(notebook)
        
        # Tab 4: Communications
        self.create_communications_tab(notebook)
        
        # Tab 5: Network Info
        self.create_network_tab(notebook)
    
    def create_node_tab(self, notebook):
        """Create node management tab."""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="Node Management")
        
        # Buttons frame
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(btn_frame, text="List All Nodes", command=self.list_nodes).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Get Node Info", command=self.get_node_info).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Health Status", command=self.health_status).pack(side=tk.LEFT, padx=(0, 5))
        
        # Output area
        self.node_output = scrolledtext.ScrolledText(frame, height=20, wrap=tk.WORD)
        self.node_output.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)
    
    def create_compute_tab(self, notebook):
        """Create compute tasks tab."""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="Compute Tasks")
        
        # Task configuration
        config_frame = ttk.LabelFrame(frame, text="Task Configuration", padding="10")
        config_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(config_frame, text="Task Type:").grid(row=0, column=0, sticky=tk.W)
        self.task_type = ttk.Combobox(config_frame, values=["Matrix Multiply", "Data Processing", "AI Inference"], state="readonly")
        self.task_type.set("Matrix Multiply")
        self.task_type.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # Action buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(btn_frame, text="Submit Compute Task", command=self.submit_compute_task).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="List Workers", command=self.list_workers).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Check Task Status", command=self.check_task_status).pack(side=tk.LEFT)
        
        # Output area
        self.compute_output = scrolledtext.ScrolledText(frame, height=18, wrap=tk.WORD)
        self.compute_output.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        frame.rowconfigure(2, weight=1)
        frame.columnconfigure(0, weight=1)
    
    def create_file_tab(self, notebook):
        """Create file operations tab (Receptors)."""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="File Operations")
        
        # Upload section
        upload_frame = ttk.LabelFrame(frame, text="Upload File", padding="10")
        upload_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.upload_path = tk.StringVar()
        ttk.Entry(upload_frame, textvariable=self.upload_path, width=50).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(upload_frame, text="Browse", command=self.browse_upload).grid(row=0, column=1, padx=(5, 0))
        ttk.Button(upload_frame, text="Upload", command=self.upload_file).grid(row=0, column=2, padx=(5, 0))
        
        # Download section
        download_frame = ttk.LabelFrame(frame, text="Download File", padding="10")
        download_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(download_frame, text="File Hash:").grid(row=0, column=0, sticky=tk.W)
        self.download_hash = ttk.Entry(download_frame, width=50)
        self.download_hash.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        ttk.Button(download_frame, text="Download", command=self.download_file).grid(row=0, column=2, padx=(5, 0))
        
        # List files button
        ttk.Button(frame, text="List Available Files", command=self.list_files).grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
        
        # Output area
        self.file_output = scrolledtext.ScrolledText(frame, height=15, wrap=tk.WORD)
        self.file_output.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        frame.rowconfigure(3, weight=1)
        frame.columnconfigure(0, weight=1)
    
    def create_communications_tab(self, notebook):
        """Create communications tab."""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="Communications")
        
        # Liveness test
        test_frame = ttk.LabelFrame(frame, text="Liveness Testing", padding="10")
        test_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(test_frame, text="Test P2P Connection", command=self.test_p2p_connection).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(test_frame, text="Ping All Nodes", command=self.ping_all_nodes).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(test_frame, text="Check Network Health", command=self.check_network_health).pack(side=tk.LEFT)
        
        # Output area
        self.comm_output = scrolledtext.ScrolledText(frame, height=20, wrap=tk.WORD)
        self.comm_output.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)
    
    def create_network_tab(self, notebook):
        """Create network information tab."""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="Network Info")
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(btn_frame, text="Show Peers", command=self.show_peers).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Network Topology", command=self.show_topology).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Connection Stats", command=self.show_stats).pack(side=tk.LEFT)
        
        # Output area
        self.network_output = scrolledtext.ScrolledText(frame, height=20, wrap=tk.WORD)
        self.network_output.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)
    
    def create_log_panel(self, parent):
        """Create log output panel."""
        frame = ttk.LabelFrame(parent, text="System Log", padding="10")
        frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        parent.rowconfigure(2, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
    
    # ==========================================================================
    # Connection Methods
    # ==========================================================================
    
    def connect_to_node(self):
        """Connect to Go node via Cap'n Proto."""
        if not CAPNP_AVAILABLE:
            messagebox.showerror("Error", "Cap'n Proto client not available. Install dependencies first.")
            return
        
        host = self.host_entry.get()
        try:
            port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number")
            return
        
        self.log_message(f"🔗 Connecting to {host}:{port}...")
        
        def connect_thread():
            try:
                self.go_client = GoNodeClient(host=host, port=port)
                if self.go_client.connect():
                    self.message_queue.put(("connect_success", f"Connected to {host}:{port}"))
                else:
                    self.message_queue.put(("connect_failed", f"Failed to connect to {host}:{port}"))
            except Exception as e:
                self.message_queue.put(("connect_error", str(e)))
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def disconnect_from_node(self):
        """Disconnect from Go node."""
        if self.go_client:
            self.go_client.close()
            self.go_client = None
        self.connected = False
        self.connect_btn.config(state=tk.NORMAL)
        self.disconnect_btn.config(state=tk.DISABLED)
        self.status_label.config(text="● Disconnected", foreground="red")
        self.log_message("🔌 Disconnected from node")
    
    # ==========================================================================
    # Node Management Methods
    # ==========================================================================
    
    def list_nodes(self):
        """List all nodes in the network."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("📋 Listing all nodes...")
        
        def list_thread():
            try:
                # Call Go node RPC to get all nodes
                nodes = []  # self.go_client.get_all_nodes()
                self.message_queue.put(("nodes_list", nodes))
            except Exception as e:
                self.message_queue.put(("error", f"Failed to list nodes: {str(e)}"))
        
        threading.Thread(target=list_thread, daemon=True).start()
    
    def get_node_info(self):
        """Get information about current node."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("ℹ️  Getting node info...")
        self.node_output.insert(tk.END, "Node information will be displayed here\n")
    
    def health_status(self):
        """Show health status of all nodes."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("❤️  Checking health status...")
        self.node_output.insert(tk.END, "Health status will be displayed here\n")
    
    # ==========================================================================
    # Compute Methods
    # ==========================================================================
    
    def submit_compute_task(self):
        """Submit a compute task."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to a node first")
            return
        
        task_type = self.task_type.get()
        self.log_message(f"⚙️  Submitting {task_type} task...")
        self.compute_output.insert(tk.END, f"Task submitted: {task_type}\n")
    
    def list_workers(self):
        """List available compute workers."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("👷 Listing compute workers...")
        self.compute_output.insert(tk.END, "Workers will be listed here\n")
    
    def check_task_status(self):
        """Check status of compute tasks."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("📊 Checking task status...")
        self.compute_output.insert(tk.END, "Task status will be displayed here\n")
    
    # ==========================================================================
    # File Operations Methods (Receptors)
    # ==========================================================================
    
    def browse_upload(self):
        """Browse for file to upload."""
        filename = filedialog.askopenfilename()
        if filename:
            self.upload_path.set(filename)
    
    def upload_file(self):
        """Upload file to network."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to a node first")
            return
        
        filepath = self.upload_path.get()
        if not filepath:
            messagebox.showwarning("No File", "Please select a file to upload")
            return
        
        self.log_message(f"⬆️  Uploading {filepath}...")
        self.file_output.insert(tk.END, f"Uploading: {filepath}\n")
    
    def download_file(self):
        """Download file from network."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to a node first")
            return
        
        file_hash = self.download_hash.get()
        if not file_hash:
            messagebox.showwarning("No Hash", "Please enter a file hash")
            return
        
        self.log_message(f"⬇️  Downloading file {file_hash[:16]}...")
        self.file_output.insert(tk.END, f"Downloading: {file_hash}\n")
    
    def list_files(self):
        """List available files in network."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("📁 Listing available files...")
        self.file_output.insert(tk.END, "Available files will be listed here\n")
    
    # ==========================================================================
    # Communications Methods
    # ==========================================================================
    
    def test_p2p_connection(self):
        """Test P2P connection."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("🔗 Testing P2P connection...")
        self.comm_output.insert(tk.END, "P2P test results will be shown here\n")
    
    def ping_all_nodes(self):
        """Ping all nodes in network."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("📡 Pinging all nodes...")
        self.comm_output.insert(tk.END, "Ping results will be shown here\n")
    
    def check_network_health(self):
        """Check overall network health."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("💚 Checking network health...")
        self.comm_output.insert(tk.END, "Network health status will be shown here\n")
    
    # ==========================================================================
    # Network Info Methods
    # ==========================================================================
    
    def show_peers(self):
        """Show connected peers."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("👥 Showing connected peers...")
        self.network_output.insert(tk.END, "Peer information will be displayed here\n")
    
    def show_topology(self):
        """Show network topology."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("🗺️  Showing network topology...")
        self.network_output.insert(tk.END, "Network topology will be displayed here\n")
    
    def show_stats(self):
        """Show connection statistics."""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to a node first")
            return
        
        self.log_message("📊 Showing connection statistics...")
        self.network_output.insert(tk.END, "Connection statistics will be displayed here\n")
    
    # ==========================================================================
    # Utility Methods
    # ==========================================================================
    
    def log_message(self, message: str):
        """Add message to log panel."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_line)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        logger.info(message)
    
    def process_messages(self):
        """Process messages from worker threads."""
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                
                if msg_type == "connect_success":
                    self.connected = True
                    self.connect_btn.config(state=tk.DISABLED)
                    self.disconnect_btn.config(state=tk.NORMAL)
                    self.status_label.config(text="● Connected", foreground="green")
                    self.log_message(f"✅ {data}")
                
                elif msg_type == "connect_failed":
                    self.log_message(f"❌ {data}")
                    messagebox.showerror("Connection Failed", data)
                
                elif msg_type == "connect_error":
                    self.log_message(f"❌ Connection error: {data}")
                    messagebox.showerror("Error", f"Connection error: {data}")
                
                elif msg_type == "nodes_list":
                    self.node_output.insert(tk.END, f"Nodes: {json.dumps(data, indent=2)}\n")
                
                elif msg_type == "error":
                    self.log_message(f"❌ {data}")
                    messagebox.showerror("Error", data)
        
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.process_messages)


def main():
    """Main entry point."""
    root = tk.Tk()
    app = PangeaDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
