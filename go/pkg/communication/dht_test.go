//go:build ignore

// This file was superseded by tests in the module root `go/dht_integration_test.go`.
// Marked ignore so it does not participate in `go test`.

package communication

import (
	"context"
	"testing"
	"time"

	"github.com/libp2p/go-libp2p/core/peer"
)

func TestLocalModeSkipsDHT(t *testing.T) {
	store := NewNodeStore()
	node, err := NewLibP2PPangeaNodeWithOptions(1, store, true, true, 0)
	if err != nil {
		t.Fatalf("failed to create node in local mode: %v", err)
	}
	defer node.cancel()

	if node.dht != nil {
		t.Error("expected dht to be nil in localMode")
	}
}

func TestWANModeInitializesDHT(t *testing.T) {
	store := NewNodeStore()
	node, err := NewLibP2PPangeaNodeWithOptions(2, store, false, true, 12000)
	if err != nil {
		t.Fatalf("failed to create node in WAN mode: %v", err)
	}
	defer node.cancel()

	if node.dht == nil {
		t.Error("expected dht to be initialized in WAN mode")
	}
}

func TestDHTPutGetValueRoundtrip(t *testing.T) {
	// Create two nodes and connect them directly, then use DHT Put/GetValue
	store1 := NewNodeStore()
	n1, err := NewLibP2PPangeaNodeWithOptions(11, store1, false, true, 12010)
	if err != nil {
		t.Fatalf("failed to create node1: %v", err)
	}
	defer n1.cancel()

	store2 := NewNodeStore()
	n2, err := NewLibP2PPangeaNodeWithOptions(12, store2, false, true, 12011)
	if err != nil {
		t.Fatalf("failed to create node2: %v", err)
	}
	defer n2.cancel()

	// Connect n1 -> n2
	pi := peer.AddrInfo{ID: n2.host.ID(), Addrs: n2.host.Addrs()}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := n1.host.Connect(ctx, pi); err != nil {
		t.Fatalf("failed to connect n1 to n2: %v", err)
	}

	if n1.dht == nil || n2.dht == nil {
		t.Fatalf("dht must be initialized for both nodes")
	}

	key := "pangea/test/value"
	value := []byte("hello encrypted shard")

	// Put value on n1
	if err := n1.dht.PutValue(ctx, key, value); err != nil {
		t.Fatalf("PutValue failed: %v", err)
	}

	// Try GetValue on n2 with retry
	var got []byte
	var lastErr error
	for i := 0; i < 10; i++ {
		ctx2, cancel2 := context.WithTimeout(context.Background(), 1*time.Second)
		v, err := n2.dht.GetValue(ctx2, key)
		cancel2()
		if err == nil {
			got = v
			break
		}
		lastErr = err
		// wait and retry
		time.Sleep(200 * time.Millisecond)
	}

	if got == nil {
		t.Fatalf("GetValue failed after retries: %v", lastErr)
	}

	if string(got) != string(value) {
		t.Errorf("value mismatch: got %s want %s", string(got), string(value))
	}
}
