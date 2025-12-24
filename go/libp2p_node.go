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

	"github.com/pangea-net/go-node/pkg/compute"
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
	nodeID          uint32
	host            host.Host
	dht             *dht.IpfsDHT
	ping            *ping.PingService
	discovery       *routing.RoutingDiscovery
	mdns            mdns.Service
	store           *NodeStore
	ctx             context.Context
	cancel          context.CancelFunc
	localMode       bool
	testMode        bool
	reachability    ReachabilityStatus
	natType         NATType
	reachabilityMu  sync.RWMutex
	computeProtocol *ComputeProtocol

	// Local stores for shards and DKG shares
	shardStore map[string]map[uint32][]byte // fileHash -> shardIndex -> data
	shardMu    sync.RWMutex

	dkgShares map[string]map[uint32][]byte // fileID -> peerID -> share bytes
	dkgMu     sync.RWMutex
}

func NewLibP2PPangeaNodeWithOptions(nodeID uint32, store *NodeStore, localMode bool, testMode bool, port int) (*LibP2PPangeaNode, error) {
	ctx, cancel := context.WithCancel(context.Background())

	connMgr, err := connmgr.NewConnManager(
		100, // low watermark
		400, // high watermark
		connmgr.WithGracePeriod(2*time.Second),
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

		// Address filtering - don't announce localhost addresses
		libp2p.AddrsFactory(func(addrs []multiaddr.Multiaddr) []multiaddr.Multiaddr {
			filtered := make([]multiaddr.Multiaddr, 0, len(addrs))
			for _, addr := range addrs {
				addrStr := addr.String()
				// Skip localhost addresses
				if !strings.Contains(addrStr, "127.0.0.1") && !strings.Contains(addrStr, "::1") {
					filtered = append(filtered, addr)
				}
			}
			return filtered
		}),
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
				fmt.Sprintf("/ip4/0.0.0.0/tcp/%d", port),      // All interfaces TCP - FIXED PORT
				fmt.Sprintf("/ip4/0.0.0.0/udp/%d/quic", port), // All interfaces QUIC - FIXED PORT
			),

			// NAT traversal - THE KEY PART! 🔥
			libp2p.EnableNATService(),   // Detect NAT status
			libp2p.EnableHolePunching(), // Attempt direct connections through NAT
		)
		if testMode {
			log.Printf("🌐 WAN MODE: Listening on port %d with NAT traversal", port)
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
	// mDNS enables automatic peer discovery on the local network (same subnet)
	notifee := &discoveryNotifee{testMode: testMode}
	mdnsService := mdns.NewMdnsService(host, PangeaDiscoveryTopic, notifee)
	log.Printf("📡 mDNS service initialized - local peers will auto-connect")

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
		shardStore:   make(map[string]map[uint32][]byte),
		dkgShares:    make(map[string]map[uint32][]byte),
	}

	// Link notifee to node for auto-connect
	notifee.node = node

	// Set stream handler for Pangea RPC protocol
	host.SetStreamHandler(protocol.ID(PangeaRPCProtocol), node.handlePangeaRPC)

	// Register network notifier to handle incoming connections
	host.Network().Notify(&networkNotifee{node: node})

	return node, nil
}

// StoreShard stores a shard for a given fileHash and index on this node
func (n *LibP2PPangeaNode) StoreShard(fileHash string, shardIndex uint32, data []byte) {
	n.shardMu.Lock()
	defer n.shardMu.Unlock()
	if _, ok := n.shardStore[fileHash]; !ok {
		n.shardStore[fileHash] = make(map[uint32][]byte)
	}
	n.shardStore[fileHash][shardIndex] = data
}

// FetchLocalShard returns shard data if present locally
func (n *LibP2PPangeaNode) FetchLocalShard(fileHash string, shardIndex uint32) ([]byte, bool) {
	n.shardMu.RLock()
	defer n.shardMu.RUnlock()
	if m, ok := n.shardStore[fileHash]; ok {
		if d, ok2 := m[shardIndex]; ok2 {
			return d, true
		}
	}
	return nil, false
}

// StoreDKGShare stores a received DKG share for a file ID
func (n *LibP2PPangeaNode) StoreDKGShare(fileID string, fromPeer uint32, share []byte) {
	n.dkgMu.Lock()
	defer n.dkgMu.Unlock()
	if _, ok := n.dkgShares[fileID]; !ok {
		n.dkgShares[fileID] = make(map[uint32][]byte)
	}
	n.dkgShares[fileID][fromPeer] = share
}

// GetLocalShare returns a locally stored share for fileID if present
func (n *LibP2PPangeaNode) GetLocalShare(fileID string) ([]byte, bool) {
	n.dkgMu.RLock()
	defer n.dkgMu.RUnlock()
	if m, ok := n.dkgShares[fileID]; ok {
		if s, ok2 := m[n.nodeID]; ok2 {
			return s, true
		}
	}
	return nil, false
}

// Start begins the libp2p node operations
func (n *LibP2PPangeaNode) Start() error {
	log.Printf("🚀 Starting libp2p Pangea node")
	log.Printf("📍 Node ID: %s", n.host.ID().String())
	log.Printf("🌐 Listening addresses:")
	for _, addrStr := range n.LocalMultiaddrs(true) {
		log.Printf("   %s", addrStr)
	}

	// Start mDNS discovery (required for local peer auto-connect)
	if n.mdns != nil {
		if err := n.mdns.Start(); err != nil {
			log.Printf("❌ Failed to start mDNS discovery: %v", err)
		} else {
			log.Printf("📡 mDNS discovery running (service: %s)", PangeaDiscoveryTopic)
		}
	}

	// Start peer discovery
	go n.discoverPeers()

	// Start connection monitoring
	go n.monitorConnections()

	// Start NAT detection and reachability monitoring
	go n.monitorReachability()

	return nil
}

// SetComputeProtocol sets the compute protocol for this node
func (n *LibP2PPangeaNode) SetComputeProtocol(cp *ComputeProtocol) {
	n.computeProtocol = cp
}

// GetComputeProtocol returns the compute protocol handler
func (n *LibP2PPangeaNode) GetComputeProtocol() *ComputeProtocol {
	return n.computeProtocol
}

// LocalMultiaddrs returns the node's listen multiaddrs with peer ID appended.
// includeLocal controls whether localhost addresses are returned (useful for
// local testing / CLI display).
func (n *LibP2PPangeaNode) LocalMultiaddrs(includeLocal bool) []string {
	addrs := make([]string, 0, len(n.host.Addrs()))
	for _, addr := range n.host.Addrs() {
		addrStr := addr.String()
		if includeLocal || (!strings.Contains(addrStr, "127.0.0.1") && !strings.Contains(addrStr, "::1")) {
			addrs = append(addrs, fmt.Sprintf("%s/p2p/%s", addr, n.host.ID()))
		}
	}
	return addrs
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

	// Log connection attempt details
	log.Printf("🔄 Attempting to connect to peer %s", shortPeerID(pi.ID))
	for _, addr := range pi.Addrs {
		log.Printf("   Address: %s", addr.String())
	}

	// Try connection with retries and increasing timeout
	var lastErr error
	for attempt := 1; attempt <= 3; attempt++ {
		timeout := time.Duration(10*attempt) * time.Second
		ctx, cancel := context.WithTimeout(n.ctx, timeout)

		log.Printf("   Attempt %d/3 (timeout: %v)", attempt, timeout)
		if err := n.host.Connect(ctx, pi); err != nil {
			lastErr = err
			log.Printf("   ❌ Attempt %d failed: %v", attempt, err)
			cancel()
			// Wait before retry
			if attempt < 3 {
				time.Sleep(2 * time.Second)
			}
			continue
		}
		cancel()
		lastErr = nil
		break
	}

	if lastErr != nil {
		return false, lastErr
	}

	// Get the peer's IP address for logging
	peerIP := "unknown"
	if len(pi.Addrs) > 0 {
		for _, addr := range pi.Addrs {
			addrStr := addr.String()
			// Extract IP from multiaddr like /ip4/192.168.1.5/tcp/7777
			if strings.Contains(addrStr, "/ip4/") {
				parts := strings.Split(addrStr, "/")
				for i, p := range parts {
					if p == "ip4" && i+1 < len(parts) {
						peerIP = parts[i+1]
						break
					}
				}
			}
		}
	}

	log.Printf("✅ Connected to peer %s (IP: %s)", shortPeerID(pi.ID), peerIP)
	log.Printf("🔗 PEER CONNECTED: PeerID=%s IP=%s", pi.ID.String(), peerIP)

	// Register this peer as a compute worker
	if n.computeProtocol != nil {
		// Default capacity for now - in the future we can query the peer
		defaultCapacity := compute.ComputeCapacity{
			CPUCores:      4,
			RAMMB:         8192,
			CurrentLoad:   0.0,
			DiskMB:        10240,
			BandwidthMbps: 100.0,
		}
		n.computeProtocol.RegisterWorker(pi.ID, defaultCapacity)
		log.Printf("👷 Registered peer %s (IP: %s) as compute worker", shortPeerID(pi.ID), peerIP)
	}

	// Ensure maps initialized
	if n.shardStore == nil {
		n.shardStore = make(map[string]map[uint32][]byte)
	}
	if n.dkgShares == nil {
		n.dkgShares = make(map[string]map[uint32][]byte)
	}

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

	// Unified RPC handler - supports small request types for testing:
	// [1] Shard fetch request: [TYPE=1][fileHashLen(2)][fileHash][shardIndex(4)] -> responds with shard bytes
	// [2] DKG share request: [TYPE=2][fileIDLen(2)][fileID] -> responds with stored share bytes

	header := make([]byte, 1)
	if _, err := io.ReadFull(stream, header); err != nil {
		log.Printf("❌ Failed to read request header: %v", err)
		return
	}

	switch header[0] {
	case 1:
		// Shard fetch
		lenBuf := make([]byte, 2)
		if _, err := io.ReadFull(stream, lenBuf); err != nil {
			log.Printf("❌ Failed to read fileHash len: %v", err)
			return
		}
		hashLen := int(lenBuf[0])<<8 | int(lenBuf[1])
		fh := make([]byte, hashLen)
		if _, err := io.ReadFull(stream, fh); err != nil {
			log.Printf("❌ Failed to read fileHash: %v", err)
			return
		}
		idxBuf := make([]byte, 4)
		if _, err := io.ReadFull(stream, idxBuf); err != nil {
			log.Printf("❌ Failed to read shard index: %v", err)
			return
		}
		shardIdx := uint32(idxBuf[0])<<24 | uint32(idxBuf[1])<<16 | uint32(idxBuf[2])<<8 | uint32(idxBuf[3])

		fileHash := string(fh)
		n.shardMu.RLock()
		if shardMap, ok := n.shardStore[fileHash]; ok {
			if data, ok2 := shardMap[shardIdx]; ok2 {
				n.shardMu.RUnlock()
				if _, err := stream.Write(data); err != nil {
					log.Printf("❌ Failed to write shard response: %v", err)
				}
				return
			}
		}
		n.shardMu.RUnlock()
		// Not found - respond with empty
		if _, err := stream.Write([]byte{}); err != nil {
			log.Printf("❌ Failed to write empty shard response: %v", err)
		}

	case 2:
		// DKG share request
		lenBuf := make([]byte, 2)
		if _, err := io.ReadFull(stream, lenBuf); err != nil {
			log.Printf("❌ Failed to read fileID len: %v", err)
			return
		}
		idLen := int(lenBuf[0])<<8 | int(lenBuf[1])
		fid := make([]byte, idLen)
		if _, err := io.ReadFull(stream, fid); err != nil {
			log.Printf("❌ Failed to read fileID: %v", err)
			return
		}
		fileID := string(fid)

		n.dkgMu.RLock()
		if shares, ok := n.dkgShares[fileID]; ok {
			if s, ok2 := shares[n.nodeID]; ok2 {
				n.dkgMu.RUnlock()
				if _, err := stream.Write(s); err != nil {
					log.Printf("❌ Failed to write share response: %v", err)
				}
				return
			}
		}
		n.dkgMu.RUnlock()
		// Not found
		if _, err := stream.Write([]byte{}); err != nil {
			log.Printf("❌ Failed to write empty share response: %v", err)
		}

	case 3:
		// Store shard on this node
		lenBuf := make([]byte, 2)
		if _, err := io.ReadFull(stream, lenBuf); err != nil {
			log.Printf("❌ Failed to read fileHash len for store: %v", err)
			return
		}
		hashLen := int(lenBuf[0])<<8 | int(lenBuf[1])
		fh := make([]byte, hashLen)
		if _, err := io.ReadFull(stream, fh); err != nil {
			log.Printf("❌ Failed to read fileHash for store: %v", err)
			return
		}
		idxBuf := make([]byte, 4)
		if _, err := io.ReadFull(stream, idxBuf); err != nil {
			log.Printf("❌ Failed to read shard index for store: %v", err)
			return
		}
		shardIdx := uint32(idxBuf[0])<<24 | uint32(idxBuf[1])<<16 | uint32(idxBuf[2])<<8 | uint32(idxBuf[3])

		// Read remaining as shard data
		dataBuf := make([]byte, 1024*1024)
		nread, _ := stream.Read(dataBuf)
		shardData := dataBuf[:nread]

		n.StoreShard(string(fh), shardIdx, shardData)
		if _, err := stream.Write([]byte("OK")); err != nil {
			log.Printf("❌ Failed to write store ack: %v", err)
		}

	case 4:
		// Store a DKG share sent by a dealer
		lenBuf := make([]byte, 2)
		if _, err := io.ReadFull(stream, lenBuf); err != nil {
			log.Printf("❌ Failed to read fileID len for share store: %v", err)
			return
		}
		idLen := int(lenBuf[0])<<8 | int(lenBuf[1])
		fid := make([]byte, idLen)
		if _, err := io.ReadFull(stream, fid); err != nil {
			log.Printf("❌ Failed to read fileID for share store: %v", err)
			return
		}
		// fromPeer
		fromBuf := make([]byte, 4)
		if _, err := io.ReadFull(stream, fromBuf); err != nil {
			log.Printf("❌ Failed to read fromPeer for share store: %v", err)
			return
		}
		fromPeer := uint32(fromBuf[0])<<24 | uint32(fromBuf[1])<<16 | uint32(fromBuf[2])<<8 | uint32(fromBuf[3])
		_ = fromPeer // currently unused by recipient
		// share len
		slenBuf := make([]byte, 4)
		if _, err := io.ReadFull(stream, slenBuf); err != nil {
			log.Printf("❌ Failed to read share len for store: %v", err)
			return
		}
		slen := int(slenBuf[0])<<24 | int(slenBuf[1])<<16 | int(slenBuf[2])<<8 | int(slenBuf[3])
		shareBuf := make([]byte, slen)
		if _, err := io.ReadFull(stream, shareBuf); err != nil {
			log.Printf("❌ Failed to read share data: %v", err)
			return
		}

		// Store share under this node's own id (the recipient) so it can be fetched by others
		n.StoreDKGShare(string(fid), n.nodeID, shareBuf)
		if _, err := stream.Write([]byte("OK")); err != nil {
			log.Printf("❌ Failed to write share store ack: %v", err)
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

// GetHost returns the libp2p host for use by other services
func (n *LibP2PPangeaNode) GetHost() host.Host {
	return n.host
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

	// Always log mDNS discoveries (it's important info)
	log.Printf("📡 mDNS discovered local peer: %s", shortPeerID(pi.ID))

	// Check if already connected
	if n.node.host.Network().Connectedness(pi.ID) == network.Connected {
		log.Printf("✓ Already connected to %s", shortPeerID(pi.ID))
		return
	}

	// Auto-connect to discovered local peers (this is the whole point of mDNS!)
	go func() {
		log.Printf("🔗 Auto-connecting to mDNS peer %s...", shortPeerID(pi.ID))
		if _, err := n.node.connectPeerInfo(pi); err != nil {
			log.Printf("❌ Failed to auto-connect to mDNS peer %s: %v", shortPeerID(pi.ID), err)
		} else {
			log.Printf("✅ Successfully connected to mDNS peer %s", shortPeerID(pi.ID))
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

// networkNotifee handles network connection events
type networkNotifee struct {
	node *LibP2PPangeaNode
}

func (n *networkNotifee) Listen(network.Network, multiaddr.Multiaddr)      {}
func (n *networkNotifee) ListenClose(network.Network, multiaddr.Multiaddr) {}
func (n *networkNotifee) Disconnected(_ network.Network, conn network.Conn) {
	log.Printf("🔌 PEER DISCONNECTED: PeerID=%s", conn.RemotePeer().String())
}

func (n *networkNotifee) Connected(_ network.Network, conn network.Conn) {
	peerID := conn.RemotePeer()
	remoteAddr := conn.RemoteMultiaddr().String()

	// Extract IP from multiaddr
	peerIP := "unknown"
	if strings.Contains(remoteAddr, "/ip4/") {
		parts := strings.Split(remoteAddr, "/")
		for i, p := range parts {
			if p == "ip4" && i+1 < len(parts) {
				peerIP = parts[i+1]
				break
			}
		}
	}

	log.Printf("🔗 PEER CONNECTED: PeerID=%s IP=%s", peerID.String(), peerIP)

	// Register this peer as a compute worker
	if n.node != nil && n.node.computeProtocol != nil {
		defaultCapacity := compute.ComputeCapacity{
			CPUCores:      4,
			RAMMB:         8192,
			CurrentLoad:   0.0,
			DiskMB:        10240,
			BandwidthMbps: 100.0,
		}
		n.node.computeProtocol.RegisterWorker(peerID, defaultCapacity)
		log.Printf("👷 Registered peer %s (IP: %s) as compute worker", shortPeerID(peerID), peerIP)
	}
}
