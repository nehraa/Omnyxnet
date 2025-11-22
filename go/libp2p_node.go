package main

import (
	"context"
	"fmt"
	"io"
	"log"
	"strings"
	"sync"
	"time"

	"github.com/libp2p/go-libp2p"
	"github.com/libp2p/go-libp2p/core/host"
	"github.com/libp2p/go-libp2p/core/network"
	"github.com/libp2p/go-libp2p/core/peer"
	"github.com/libp2p/go-libp2p/core/protocol"
	"github.com/multiformats/go-multiaddr"

	dht "github.com/libp2p/go-libp2p-kad-dht"
	"github.com/libp2p/go-libp2p/p2p/discovery/mdns"
	"github.com/libp2p/go-libp2p/p2p/discovery/routing"
	"github.com/libp2p/go-libp2p/p2p/muxer/yamux"
	"github.com/libp2p/go-libp2p/p2p/net/connmgr"
	"github.com/libp2p/go-libp2p/p2p/protocol/ping"
	"github.com/libp2p/go-libp2p/p2p/security/noise"
	quic "github.com/libp2p/go-libp2p/p2p/transport/quic"
	"github.com/libp2p/go-libp2p/p2p/transport/tcp"
)

const (
	// Protocol IDs for Pangea Net
	PangeaRPCProtocol    = "/pangea/rpc/1.0.0"
	PangeaDiscoveryTopic = "pangea-network"
)

// ReachabilityStatus represents the NAT reachability status
type ReachabilityStatus string

const (
	ReachabilityUnknown ReachabilityStatus = "unknown"
	ReachabilityPublic  ReachabilityStatus = "public"  // Directly reachable
	ReachabilityPrivate ReachabilityStatus = "private" // Behind NAT
	ReachabilityRelay   ReachabilityStatus = "relay"   // Using relay
)

// NATType represents the type of NAT detected
type NATType string

const (
	NATTypeUnknown        NATType = "unknown"
	NATTypeNone           NATType = "none"            // No NAT (public IP)
	NATTypeFullCone       NATType = "full_cone"       // Easy to traverse
	NATTypeRestricted     NATType = "restricted"      // Moderate difficulty
	NATTypePortRestricted NATType = "port_restricted" // Harder to traverse
	NATTypeSymmetric      NATType = "symmetric"       // Very difficult
)

// LibP2PPangeaNode represents a Pangea node using libp2p
type LibP2PPangeaNode struct {
	nodeID         uint32
	host           host.Host
	dht            *dht.IpfsDHT
	ping           *ping.PingService
	discovery      *routing.RoutingDiscovery
	mdns           mdns.Service
	store          *NodeStore
	ctx            context.Context
	cancel         context.CancelFunc
	localMode      bool
	testMode       bool
	reachability   ReachabilityStatus
	natType        NATType
	reachabilityMu sync.RWMutex
}

// NewLibP2PPangeaNode creates a new libp2p-powered Pangea node
func NewLibP2PPangeaNode(nodeID uint32, store *NodeStore) (*LibP2PPangeaNode, error) {
	return NewLibP2PPangeaNodeWithOptions(nodeID, store, false, false)
}

// NewLibP2PPangeaNodeWithOptions creates a new libp2p node with specific options
func NewLibP2PPangeaNodeWithOptions(nodeID uint32, store *NodeStore, localMode, testMode bool) (*LibP2PPangeaNode, error) {
	ctx, cancel := context.WithCancel(context.Background())

	// Create connection manager with limits
	connMgr, err := connmgr.NewConnManager(
		10,  // Low watermark
		100, // High watermark
		connmgr.WithGracePeriod(time.Minute),
	)
	if err != nil {
		cancel()
		return nil, fmt.Errorf("failed to create connection manager: %w", err)
	}

	var libp2pOptions []libp2p.Option

	// Basic configuration
	libp2pOptions = append(libp2pOptions,
		// Network transports - TCP, QUIC for different scenarios
		libp2p.Transport(tcp.NewTCPTransport),
		libp2p.Transport(quic.NewTransport),

		// Security and multiplexing
		libp2p.Security(noise.ID, noise.New), // Noise Protocol for security
		libp2p.Muxer(yamux.ID, yamux.DefaultTransport),

		// Connection management
		libp2p.ConnectionManager(connMgr),

		// Resource management
		libp2p.ResourceManager(&network.NullResourceManager{}),
	)

	// Configure listen addresses based on mode
	if localMode {
		// Local mode: only bind to localhost and use random ports
		libp2pOptions = append(libp2pOptions,
			libp2p.ListenAddrStrings(
				"/ip4/127.0.0.1/tcp/0",      // Localhost TCP
				"/ip4/127.0.0.1/udp/0/quic", // Localhost QUIC
			),
		)
		if testMode {
			log.Printf("🏠 LOCAL MODE: Binding only to localhost")
		}
	} else {
		// WAN mode: bind to all interfaces with NAT traversal
		libp2pOptions = append(libp2pOptions,
			libp2p.ListenAddrStrings(
				"/ip4/0.0.0.0/tcp/0",      // All interfaces TCP
				"/ip4/0.0.0.0/udp/0/quic", // All interfaces QUIC
			),

			// NAT traversal - THE KEY PART! 🔥
			libp2p.EnableNATService(),   // Detect NAT status
			libp2p.EnableHolePunching(), // Attempt direct connections through NAT
		)
		if testMode {
			log.Printf("🌐 WAN MODE: Full NAT traversal enabled")
		}
	}

	// Create libp2p host
	host, err := libp2p.New(libp2pOptions...)
	if err != nil {
		cancel()
		return nil, fmt.Errorf("failed to create libp2p host: %w", err)
	}

	var kadDHT *dht.IpfsDHT
	var routingDiscovery *routing.RoutingDiscovery

	if !localMode {
		// Only create DHT for WAN mode
		kadDHT, err = dht.New(ctx, host, dht.Mode(dht.ModeServer))
		if err != nil {
			host.Close()
			cancel()
			return nil, fmt.Errorf("failed to create DHT: %w", err)
		}

		// Bootstrap DHT with known nodes (IPFS bootstrap by default)
		if err := kadDHT.Bootstrap(ctx); err != nil {
			if testMode {
				log.Printf("⚠️  DHT bootstrap failed (this is normal in test mode): %v", err)
			}
			// Don't fail completely - DHT bootstrap can fail in test environments
		}

		// Create routing discovery for content-based discovery
		routingDiscovery = routing.NewRoutingDiscovery(kadDHT)
	} else if testMode {
		log.Printf("🏠 LOCAL MODE: Skipping DHT initialization")
	}

	// Create ping service for connection health
	pingService := ping.NewPingService(host)

	// Create mDNS discovery for local network - works in both modes
	var mdnsService mdns.Service
	notifee := &discoveryNotifee{testMode: testMode}
	mdnsService = mdns.NewMdnsService(host, PangeaDiscoveryTopic, notifee)
	if mdnsService == nil {
		if testMode {
			log.Printf("⚠️  mDNS service unavailable in this environment")
		}
	} else if testMode {
		log.Printf("📡 mDNS service initialized for local discovery")
	}

	node := &LibP2PPangeaNode{
		nodeID:       nodeID,
		host:         host,
		dht:          kadDHT,
		ping:         pingService,
		discovery:    routingDiscovery,
		mdns:         mdnsService,
		store:        store,
		ctx:          ctx,
		cancel:       cancel,
		localMode:    localMode,
		testMode:     testMode,
		reachability: ReachabilityUnknown,
		natType:      NATTypeUnknown,
	}

	if notifee != nil {
		notifee.node = node
	}

	// Set stream handler for Pangea RPC protocol
	host.SetStreamHandler(protocol.ID(PangeaRPCProtocol), node.handlePangeaRPC)

	return node, nil
}

// Start begins the libp2p node operations
func (n *LibP2PPangeaNode) Start() error {
	log.Printf("🚀 Starting libp2p Pangea node")
	log.Printf("📍 Node ID: %s", n.host.ID().String())
	log.Printf("🌐 Listening addresses:")
	for _, addr := range n.host.Addrs() {
		log.Printf("   %s/p2p/%s", addr, n.host.ID())
	}

	// Start peer discovery
	go n.discoverPeers()

	// Start connection monitoring
	go n.monitorConnections()

	// Start NAT detection and reachability monitoring
	go n.monitorReachability()

	return nil
}

// discoverPeers handles both local and global peer discovery
func (n *LibP2PPangeaNode) discoverPeers() {
	if n.discovery == nil {
		if n.testMode {
			log.Printf("📡 DHT discovery disabled; relying on mDNS/local peers only")
		}
		return
	}

	if _, err := n.discovery.Advertise(n.ctx, PangeaDiscoveryTopic); err != nil {
		log.Printf("❌ Failed to advertise on DHT: %v", err)
	} else {
		log.Printf("📢 Advertising on DHT topic: %s", PangeaDiscoveryTopic)
	}

	// Continuously discover peers
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-n.ctx.Done():
			return
		case <-ticker.C:
			n.findAndConnectPeers()
		}
	}
}

// findAndConnectPeers discovers and connects to Pangea peers
func (n *LibP2PPangeaNode) findAndConnectPeers() {
	if n.discovery == nil {
		return
	}

	log.Printf("🔍 Discovering Pangea peers...")

	peerChan, err := n.discovery.FindPeers(n.ctx, PangeaDiscoveryTopic)
	if err != nil {
		log.Printf("❌ Failed to find peers: %v", err)
		return
	}

	successfulConnections := 0
	for pi := range peerChan {
		connected, err := n.connectPeerInfo(pi)
		if err != nil {
			log.Printf("❌ Failed to connect to peer %s: %v", shortPeerID(pi.ID), err)
			continue
		}
		if connected {
			successfulConnections++
		}
		if successfulConnections >= 5 {
			break
		}
	}
}

// connectPeerInfo dials the provided peer info if needed.
func (n *LibP2PPangeaNode) connectPeerInfo(pi peer.AddrInfo) (bool, error) {
	if pi.ID == "" {
		return false, fmt.Errorf("peer info missing ID")
	}

	if pi.ID == n.host.ID() {
		return false, nil
	}

	if n.host.Network().Connectedness(pi.ID) == network.Connected {
		return false, nil
	}

	ctx, cancel := context.WithTimeout(n.ctx, 10*time.Second)
	defer cancel()

	if err := n.host.Connect(ctx, pi); err != nil {
		return false, err
	}

	log.Printf("✅ Connected to peer %s", shortPeerID(pi.ID))
	go n.testConnection(pi.ID)
	return true, nil
}

// testConnection tests connection quality with ping
func (n *LibP2PPangeaNode) testConnection(peerID peer.ID) {
	ctx, cancel := context.WithTimeout(n.ctx, 5*time.Second)
	defer cancel()

	result := <-n.ping.Ping(ctx, peerID)
	if result.Error != nil {
		log.Printf("❌ Ping failed to %s: %v", peerID.String()[:8], result.Error)
	} else {
		log.Printf("📊 Ping to %s: %v", peerID.String()[:8], result.RTT)

		latency := float32(result.RTT.Milliseconds())
		if ok := n.store.UpdateLatency(n.nodeID, latency); !ok && n.testMode {
			log.Printf("⚠️  Unable to update latency for node %d", n.nodeID)
		}
	}
}

// handlePangeaRPC handles incoming RPC streams
func (n *LibP2PPangeaNode) handlePangeaRPC(stream network.Stream) {
	defer stream.Close()

	log.Printf("📞 Incoming RPC from peer %s", stream.Conn().RemotePeer().String()[:8])

	// Here you would bridge to your existing Cap'n Proto RPC system
	// For now, we'll implement a simple echo protocol

	buffer := make([]byte, 1024)
	for {
		read, err := stream.Read(buffer)
		if err != nil {
			if err != io.EOF {
				log.Printf("❌ Stream read error: %v", err)
			}
			return
		}

		message := string(buffer[:read])
		log.Printf("📨 Received: %s", message)

		response := fmt.Sprintf("PONG from %s: %s", stream.Conn().LocalPeer().String()[:8], message)
		if _, err := stream.Write([]byte(response)); err != nil {
			log.Printf("❌ Stream write error: %v", err)
			return
		}
	}
}

// monitorConnections monitors connection health and NAT status
func (n *LibP2PPangeaNode) monitorConnections() {
	ticker := time.NewTicker(15 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-n.ctx.Done():
			return
		case <-ticker.C:
			n.reportConnectionStatus()
		}
	}
}

// reportConnectionStatus reports current network status
func (n *LibP2PPangeaNode) reportConnectionStatus() {
	peers := n.host.Network().Peers()
	conns := n.host.Network().Conns()

	log.Printf("🌐 Network Status:")
	log.Printf("   Connected peers: %d", len(peers))
	log.Printf("   Active connections: %d", len(conns))

	// Report connection details
	for _, conn := range conns {
		localAddr := conn.LocalMultiaddr()
		remoteAddr := conn.RemoteMultiaddr()

		// Determine connection type (direct, relay, etc.)
		connType := "direct"
		if strings.Contains(remoteAddr.String(), "/p2p-circuit/") {
			connType = "relay"
		}

		log.Printf("   %s ↔ %s (%s)",
			localAddr,
			remoteAddr,
			connType)
	}

	// Report reachability status
	n.reachabilityMu.RLock()
	reachability := n.reachability
	natType := n.natType
	n.reachabilityMu.RUnlock()

	log.Printf("   Reachability: %s (NAT: %s)", reachability, natType)
}

// monitorReachability detects NAT type and reachability status
func (n *LibP2PPangeaNode) monitorReachability() {
	// UNTESTABLE: Requires real WAN deployment to detect actual NAT
	// This implementation provides the structure for production use

	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	// Initial detection
	if !n.localMode {
		n.detectReachability()
	}

	for {
		select {
		case <-n.ctx.Done():
			return
		case <-ticker.C:
			if !n.localMode {
				n.detectReachability()
			}
		}
	}
}

// detectReachability performs NAT and reachability detection
func (n *LibP2PPangeaNode) detectReachability() {
	// In local mode, always report as private
	if n.localMode {
		n.reachabilityMu.Lock()
		n.reachability = ReachabilityPrivate
		n.natType = NATTypeNone
		n.reachabilityMu.Unlock()
		return
	}

	// Check listening addresses for public IPs
	hasPublicAddr := false
	hasPrivateAddr := false
	usingRelay := false

	for _, addr := range n.host.Addrs() {
		addrStr := addr.String()

		// Check for relay
		if strings.Contains(addrStr, "/p2p-circuit/") {
			usingRelay = true
			continue
		}

		// Check for private vs public IP
		if strings.Contains(addrStr, "127.0.0.1") ||
			strings.Contains(addrStr, "192.168.") ||
			strings.Contains(addrStr, "10.") ||
			strings.Contains(addrStr, "172.16.") {
			hasPrivateAddr = true
		} else if strings.Contains(addrStr, "/ip4/") || strings.Contains(addrStr, "/ip6/") {
			hasPublicAddr = true
		}
	}

	// Determine reachability and NAT type
	n.reachabilityMu.Lock()
	defer n.reachabilityMu.Unlock()

	if hasPublicAddr && !hasPrivateAddr {
		n.reachability = ReachabilityPublic
		n.natType = NATTypeNone
	} else if hasPrivateAddr && !hasPublicAddr {
		n.reachability = ReachabilityPrivate
		// Basic NAT type detection based on connection success rate
		// In production, would use STUN protocol for accurate detection
		conns := n.host.Network().Conns()
		if len(conns) > 0 {
			// If we have successful connections, likely port-restricted or better
			n.natType = NATTypePortRestricted
		} else {
			// No connections could indicate symmetric NAT
			n.natType = NATTypeSymmetric
		}
	} else if usingRelay {
		n.reachability = ReachabilityRelay
		n.natType = NATTypeSymmetric // Relay usually means difficult NAT
	} else {
		n.reachability = ReachabilityUnknown
		n.natType = NATTypeUnknown
	}

	if n.testMode {
		log.Printf("🔍 Detected reachability: %s (NAT: %s)", n.reachability, n.natType)
	}
}

// GetReachabilityStatus returns the current reachability and NAT type
func (n *LibP2PPangeaNode) GetReachabilityStatus() (ReachabilityStatus, NATType) {
	n.reachabilityMu.RLock()
	defer n.reachabilityMu.RUnlock()
	return n.reachability, n.natType
}

// ConnectToPeer connects to a specific peer by address
func (n *LibP2PPangeaNode) ConnectToPeer(addr string) error {
	// Parse multiaddr (e.g., "/ip4/192.168.1.100/tcp/4001/p2p/QmPeer...")
	pi, err := parseMultiaddr(addr)
	if err != nil {
		return fmt.Errorf("invalid peer address: %w", err)
	}

	connected, err := n.connectPeerInfo(pi)
	if err != nil {
		return fmt.Errorf("failed to connect to peer: %w", err)
	}
	if !connected {
		log.Printf("ℹ️  Already connected to peer %s", shortPeerID(pi.ID))
	}
	return nil
}

// GetConnectedPeers returns information about connected peers
func (n *LibP2PPangeaNode) GetConnectedPeers() []PeerInfo {
	peers := n.host.Network().Peers()
	result := make([]PeerInfo, 0, len(peers))

	for _, peerID := range peers {
		conn := n.host.Network().ConnsToPeer(peerID)
		if len(conn) > 0 {
			result = append(result, PeerInfo{
				ID:      peerID.String(),
				Address: conn[0].RemoteMultiaddr().String(),
				Status:  "connected",
			})
		}
	}

	return result
}

type PeerInfo struct {
	ID      string `json:"id"`
	Address string `json:"address"`
	Status  string `json:"status"`
}

// Stop gracefully shuts down the libp2p node
func (n *LibP2PPangeaNode) Stop() error {
	log.Printf("🛑 Shutting down libp2p Pangea node...")

	n.cancel()

	if n.mdns != nil {
		if err := n.mdns.Close(); err != nil {
			log.Printf("❌ Error closing mDNS: %v", err)
		}
	}

	if n.dht != nil {
		if err := n.dht.Close(); err != nil {
			log.Printf("❌ Error closing DHT: %v", err)
		}
	}

	if err := n.host.Close(); err != nil {
		log.Printf("❌ Error closing libp2p host: %v", err)
		return err
	}

	log.Printf("✅ libp2p Pangea node stopped")
	return nil
}

// discoveryNotifee handles peer discovery notifications
type discoveryNotifee struct {
	node     *LibP2PPangeaNode
	testMode bool
}

func (n *discoveryNotifee) HandlePeerFound(pi peer.AddrInfo) {
	if n == nil || n.node == nil {
		return
	}

	if n.testMode {
		log.Printf("🔍 mDNS discovered local peer: %s", shortPeerID(pi.ID))
	}

	go func() {
		if _, err := n.node.connectPeerInfo(pi); err != nil && n.testMode {
			log.Printf("❌ Failed to connect to mDNS peer %s: %v", shortPeerID(pi.ID), err)
		}
	}()
}

// Helper function to parse multiaddr string into peer info
func parseMultiaddr(addr string) (peer.AddrInfo, error) {
	maddr, err := multiaddr.NewMultiaddr(addr)
	if err != nil {
		return peer.AddrInfo{}, err
	}
	info, err := peer.AddrInfoFromP2pAddr(maddr)
	if err != nil {
		return peer.AddrInfo{}, err
	}
	return *info, nil
}

func shortPeerID(id peer.ID) string {
	value := id.String()
	if len(value) <= 8 {
		return value
	}
	return value[:8]
}
