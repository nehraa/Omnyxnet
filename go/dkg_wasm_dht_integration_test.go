package main

import (
	"context"
	"testing"
	"time"

	cid "github.com/ipfs/go-cid"
	mh "github.com/multiformats/go-multihash"

	"github.com/libp2p/go-libp2p/core/peer"
	"github.com/pangea-net/go-node/pkg/crypto/dkg"
)

func TestDKG_CES_DHT_Flow(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	// Setup small DHT mesh like previous tests
	store1 := NewNodeStore()
	n1, err := NewLibP2PPangeaNodeWithOptions(201, store1, false, true, 12210)
	if err != nil {
		t.Fatalf("failed to create node1: %v", err)
	}
	defer n1.cancel()

	store2 := NewNodeStore()
	n2, err := NewLibP2PPangeaNodeWithOptions(202, store2, false, true, 12211)
	if err != nil {
		t.Fatalf("failed to create node2: %v", err)
	}
	defer n2.cancel()

	store3 := NewNodeStore()
	n3, err := NewLibP2PPangeaNodeWithOptions(203, store3, false, true, 12212)
	if err != nil {
		t.Fatalf("failed to create node3: %v", err)
	}
	defer n3.cancel()

	// Mesh connect
	if err := n1.host.Connect(ctx, peer.AddrInfo{ID: n2.host.ID(), Addrs: n2.host.Addrs()}); err != nil {
		t.Fatalf("connect n1->n2 failed: %v", err)
	}
	if err := n1.host.Connect(ctx, peer.AddrInfo{ID: n3.host.ID(), Addrs: n3.host.Addrs()}); err != nil {
		t.Fatalf("connect n1->n3 failed: %v", err)
	}
	if err := n2.host.Connect(ctx, peer.AddrInfo{ID: n3.host.ID(), Addrs: n3.host.Addrs()}); err != nil {
		t.Fatalf("connect n2->n3 failed: %v", err)
	}

	// Bootstrap
	_ = n1.dht.Bootstrap(ctx)
	_ = n2.dht.Bootstrap(ctx)
	_ = n3.dht.Bootstrap(ctx)

	// Simulate file upload: derive key via DKG
	fileID := "integration-file-1"
	fileKey, err := dkg.RequestFileKey(context.Background(), fileID)
	if err != nil {
		t.Fatalf("RequestFileKey failed: %v", err)
	}
	var keyArr [32]byte
	copy(keyArr[:], fileKey)

	// Create CES pipeline with explicit key and process data
	pipeline := NewCESPipelineWithKey(1, keyArr)
	if pipeline == nil {
		t.Fatalf("Failed to create CES pipeline with key")
	}
	defer pipeline.Close()

	input := []byte("this is secret file content for DKG+CES+DHT test")
	shards, err := pipeline.Process(input)
	if err != nil {
		t.Fatalf("CES Process failed: %v", err)
	}

	// Sanity: reconstruct locally
	present := make([]bool, len(shards))
	for i := range present {
		present[i] = true
	}
	reconstructed, err := pipeline.Reconstruct(shards, present)
	if err != nil {
		t.Fatalf("Reconstruct failed: %v", err)
	}
	if string(reconstructed) != string(input) {
		t.Fatalf("reconstructed mismatch")
	}

	// Announce first shard CID on DHT from n1
	shard0 := shards[0].Data
	mhash, err := mh.Sum(shard0, mh.SHA2_256, -1)
	if err != nil {
		t.Fatalf("multihash sum failed: %v", err)
	}
	c := cid.NewCidV1(cid.Raw, mhash)
	if err := n1.dht.Provide(ctx, c, true); err != nil {
		t.Fatalf("Provide failed: %v", err)
	}

	// Find providers from n2
	found := false
	for i := 0; i < 20; i++ {
		pc := n2.dht.FindProvidersAsync(ctx, c, 10)
		for p := range pc {
			if p.ID == n1.host.ID() {
				found = true
				break
			}
		}
		if found {
			break
		}
		time.Sleep(100 * time.Millisecond)
	}
	if !found {
		t.Fatalf("provider not found for shard CID")
	}
}
