package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"
)

func main() {
	var (
		nodeID    = flag.Uint("node-id", 1, "Node ID for this instance")
		capnpAddr = flag.String("capnp-addr", ":8080", "Cap'n Proto server address")
		p2pAddr   = flag.String("p2p-addr", ":9090", "P2P network listener address (legacy mode)")
		peerAddrs = flag.String("peers", "", "Comma-separated list of peer addresses")
		useLibp2p = flag.Bool("libp2p", true, "Use libp2p for P2P networking (recommended)")
		localMode = flag.Bool("local", false, "Local testing mode (mDNS discovery only)")
		testMode  = flag.Bool("test", false, "Enable testing mode with debug output")
	)
	flag.Parse()

	if *testMode {
		log.SetFlags(log.LstdFlags | log.Lshortfile)
		log.Printf("🧪 TESTING MODE ENABLED")
	}

	log.Printf("🚀 Starting Pangea Net Go Node (ID: %d)", *nodeID)
	if *localMode {
		log.Printf("🏠 LOCAL TESTING MODE - Only local network discovery")
	}

	// Initialize node store
	store := NewNodeStore()

	// Create initial node entry
	node := store.CreateNode(uint32(*nodeID))
	log.Printf("✅ Created node %d with status: %v", node.ID, node.Status)

	// Create shared memory manager for Go-Python data streaming
	shmMgr := NewSharedMemoryManager()
	defer shmMgr.CloseAll()

	// Network adapter will be set based on which P2P implementation we use
	var networkAdapter NetworkAdapter

	// Choose P2P implementation
	if *useLibp2p {
		// Use libp2p (recommended for production)
		libp2pNode, err := NewLibP2PPangeaNodeWithOptions(uint32(*nodeID), store, *localMode, *testMode)
		if err != nil {
			log.Fatalf("❌ Failed to create libp2p node: %v", err)
		}

		// Configure for local or WAN mode
		if *localMode {
			log.Printf("🏠 Configuring for local network only")
			// In local mode, disable DHT bootstrapping to external nodes
			// This will be handled in the Start() method
		}

		if err := libp2pNode.Start(); err != nil {
			log.Fatalf("❌ Failed to start libp2p node: %v", err)
		}

		// Note: The communication service (go/pkg/communication/communication.go)
		// provides always-on chat/voice/video message handling.
		// It can be integrated by calling:
		//   commService := communication.NewCommunicationService(libp2pNode.GetHost(), communication.Config{})
		//   commService.Start()
		// Messages are automatically stored in ~/.pangea/communication/chat_history.json

		// Create network adapter for libp2p
		networkAdapter = NewLibP2PAdapter(libp2pNode, store)

		// Start Cap'n Proto server for Python communication
		go func() {
			log.Printf("🔌 Starting Cap'n Proto server on %s", *capnpAddr)
			if err := StartCapnpServer(store, networkAdapter, shmMgr, *capnpAddr); err != nil {
				log.Fatalf("❌ Failed to start Cap'n Proto server: %v", err)
			}
		}()

		// Connect to specified peers
		if *peerAddrs != "" {
			peers := strings.Split(*peerAddrs, ",")
			for _, peerAddr := range peers {
				peerAddr = strings.TrimSpace(peerAddr)
				if peerAddr == "" {
					continue
				}
				log.Printf("🔗 Connecting to peer: %s", peerAddr)
				if err := libp2pNode.ConnectToPeer(peerAddr); err != nil {
					log.Printf("❌ Failed to connect to peer %s: %v", peerAddr, err)
				}
			}
		}

		// Wait for interrupt signal
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

		if *testMode {
			go func() {
				ticker := time.NewTicker(5 * time.Second)
				defer ticker.Stop()
				// In test mode, periodically report status
				for {
					select {
					case <-sigChan:
						return
					case <-ticker.C:
						peers := libp2pNode.GetConnectedPeers()
						log.Printf("📊 Connected peers: %d", len(peers))
						for i, peer := range peers {
							if i < 3 { // Limit output
								log.Printf("   Peer %d: %s", i+1, peer.ID[:16]+"...")
							}
						}
					}
				}
			}()
		}

		log.Println("🌐 Node running. Press Ctrl+C to stop.")
		<-sigChan

		log.Println("🛑 Shutting down...")
		libp2pNode.Stop()
		log.Println("✅ Shutdown complete")

	} else {
		// Use legacy custom P2P implementation
		log.Printf("⚠️  Using legacy P2P implementation")
		p2pNode, err := NewP2PNode(uint32(*nodeID), store)
		if err != nil {
			log.Fatalf("❌ Failed to create P2P node: %v", err)
		}

		if err := p2pNode.Start(*p2pAddr); err != nil {
			log.Fatalf("❌ Failed to start P2P node: %v", err)
		}

		// Create network adapter for legacy P2P
		networkAdapter = NewLegacyP2PAdapter(p2pNode, store)

		// Start Cap'n Proto server for Python communication
		go func() {
			log.Printf("🔌 Starting Cap'n Proto server on %s", *capnpAddr)
			if err := StartCapnpServer(store, networkAdapter, shmMgr, *capnpAddr); err != nil {
				log.Fatalf("❌ Failed to start Cap'n Proto server: %v", err)
			}
		}()

		// Connect to peers if specified
		if *peerAddrs != "" {
			peers := strings.Split(*peerAddrs, ",")
			for _, peerAddr := range peers {
				parts := strings.Split(strings.TrimSpace(peerAddr), ":")
				if len(parts) >= 3 {
					// Format: id:host:port
					addr := fmt.Sprintf("%s:%s", parts[1], parts[2])
					log.Printf("🔗 Connecting to peer: %s", addr)
					// Parse peer ID and connect
					// This would need proper implementation
				}
			}
		}

		// Wait for interrupt signal
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

		log.Println("🌐 Node running. Press Ctrl+C to stop.")
		<-sigChan

		log.Println("🛑 Shutting down...")
		p2pNode.Stop()
		log.Println("✅ Shutdown complete")
	}
}
