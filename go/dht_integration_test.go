package main

import (
	"context"
	"testing"
	"time"

	cid "github.com/ipfs/go-cid"
	mh "github.com/multiformats/go-multihash"

	"github.com/libp2p/go-libp2p/core/peer"
)

func TestLocalModeSkipsDHT_Main(t *testing.T) {
	store := NewNodeStore()
	node, err := NewLibP2PPangeaNodeWithOptions(101, store, true, true, 0)
	if err != nil {
		t.Fatalf("failed to create node in local mode: %v", err)
	}
	defer node.cancel()

	if node.dht != nil {
		t.Error("expected dht to be nil in localMode")
	}
}

func TestWANModeInitializesDHT_Main(t *testing.T) {
	store := NewNodeStore()
	node, err := NewLibP2PPangeaNodeWithOptions(102, store, false, true, 12100)
	if err != nil {
		t.Fatalf("failed to create node in WAN mode: %v", err)
	}
	defer node.cancel()

	if node.dht == nil {
		t.Error("expected dht to be initialized in WAN mode")
	}
}

func TestDHTPutGetValueRoundtrip_Main(t *testing.T) {
	store1 := NewNodeStore()
	n1, err := NewLibP2PPangeaNodeWithOptions(111, store1, false, true, 12110)
	if err != nil {
		t.Fatalf("failed to create node1: %v", err)
	}
	defer n1.cancel()

	store2 := NewNodeStore()
	n2, err := NewLibP2PPangeaNodeWithOptions(112, store2, false, true, 12111)
	if err != nil {
		t.Fatalf("failed to create node2: %v", err)
	}
	defer n2.cancel()

	// Create helper third node to improve DHT routing
	store3 := NewNodeStore()
	n3, err := NewLibP2PPangeaNodeWithOptions(13, store3, false, true, 12112)
	if err != nil {
		t.Fatalf("failed to create node3: %v", err)
	}
	defer n3.cancel()

	// Connect nodes into a small mesh
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := n1.host.Connect(ctx, peer.AddrInfo{ID: n2.host.ID(), Addrs: n2.host.Addrs()}); err != nil {
		t.Fatalf("failed to connect n1 to n2: %v", err)
	}
	if err := n1.host.Connect(ctx, peer.AddrInfo{ID: n3.host.ID(), Addrs: n3.host.Addrs()}); err != nil {
		t.Fatalf("failed to connect n1 to n3: %v", err)
	}
	if err := n2.host.Connect(ctx, peer.AddrInfo{ID: n3.host.ID(), Addrs: n3.host.Addrs()}); err != nil {
		t.Fatalf("failed to connect n2 to n3: %v", err)
	}

	// Bootstrap DHTs explicitly to populate routing tables
	if err := n1.dht.Bootstrap(ctx); err != nil {
		t.Logf("n1 bootstrap warning: %v", err)
	}
	if err := n2.dht.Bootstrap(ctx); err != nil {
		t.Logf("n2 bootstrap warning: %v", err)
	}
	if err := n3.dht.Bootstrap(ctx); err != nil {
		t.Logf("n3 bootstrap warning: %v", err)
	}

	if n1.dht == nil || n2.dht == nil {
		t.Fatalf("dht must be initialized for both nodes")
	}

	value := []byte("hello encrypted shard")

	// Create CID for the content and Provide it on n1
	mhash, err := mh.Sum(value, mh.SHA2_256, -1)
	if err != nil {
		t.Fatalf("failed to compute multihash: %v", err)
	}
	c := cid.NewCidV1(cid.Raw, mhash)

	if err := n1.dht.Provide(ctx, c, true); err != nil {
		t.Fatalf("Provide failed: %v", err)
	}

	// Try to find providers from n2
	var found bool
	for i := 0; i < 20; i++ {
		ctx2, cancel2 := context.WithTimeout(context.Background(), 500*time.Millisecond)
		provChan := n2.dht.FindProvidersAsync(ctx2, c, 10)
		for p := range provChan {
			if p.ID == n1.host.ID() {
				found = true
				cancel2()
				break
			}
		}
		cancel2()
		if found {
			break
		}
		time.Sleep(100 * time.Millisecond)
	}

	if !found {
		t.Fatalf("failed to find provider for CID %s", c.String())
	}
}
