package main

import (
	"context"
	"testing"
	"time"

	"github.com/libp2p/go-libp2p/core/peer"
	"github.com/pangea-net/go-node/pkg/crypto/dkg"
)

func TestShamirDKG_DistributeAndReconstruct_Distributed(t *testing.T) {
	store1 := NewNodeStore()
	n1, err := NewLibP2PPangeaNodeWithOptions(301, store1, false, true, 12310)
	if err != nil {
		t.Fatalf("failed to create node1: %v", err)
	}
	defer n1.cancel()

	store2 := NewNodeStore()
	n2, err := NewLibP2PPangeaNodeWithOptions(302, store2, false, true, 12311)
	if err != nil {
		t.Fatalf("failed to create node2: %v", err)
	}
	defer n2.cancel()

	store3 := NewNodeStore()
	n3, err := NewLibP2PPangeaNodeWithOptions(303, store3, false, true, 12312)
	if err != nil {
		t.Fatalf("failed to create node3: %v", err)
	}
	defer n3.cancel()

	// Create adapters
	lib1 := NewLibP2PAdapter(n1, store1)
	lib2 := NewLibP2PAdapter(n2, store2)
	lib3 := NewLibP2PAdapter(n3, store3)

	// Connect peers
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := n1.host.Connect(ctx, peer.AddrInfo{ID: n2.host.ID(), Addrs: n2.host.Addrs()}); err != nil {
		t.Fatalf("connect n1->n2 failed: %v", err)
	}
	if err := n1.host.Connect(ctx, peer.AddrInfo{ID: n3.host.ID(), Addrs: n3.host.Addrs()}); err != nil {
		t.Fatalf("connect n1->n3 failed: %v", err)
	}
	if err := n2.host.Connect(ctx, peer.AddrInfo{ID: n3.host.ID(), Addrs: n3.host.Addrs()}); err != nil {
		t.Fatalf("connect n2->n3 failed: %v", err)
	}

	// Map peer strings for adapters so they can address one another
	lib1.peerIDToUint32[string(n2.host.ID())] = 2
	lib1.peerIDToUint32[string(n3.host.ID())] = 3
	lib1.uint32ToPeerID[2] = n2.host.ID().String()
	lib1.uint32ToPeerID[3] = n3.host.ID().String()

	lib2.peerIDToUint32[string(n1.host.ID())] = 1
	lib2.peerIDToUint32[string(n3.host.ID())] = 3
	lib2.uint32ToPeerID[1] = n1.host.ID().String()
	lib2.uint32ToPeerID[3] = n3.host.ID().String()

	lib3.peerIDToUint32[string(n1.host.ID())] = 1
	lib3.peerIDToUint32[string(n2.host.ID())] = 2
	lib3.uint32ToPeerID[1] = n1.host.ID().String()
	lib3.uint32ToPeerID[2] = n2.host.ID().String()

	// Distribute key from node1 (dealer)
	fileID := "real-dkg-test-file"
	participants := []uint32{2, 3}
	threshold := 2
	key, err := dkg.RequestFileKeyDistributed(context.Background(), fileID, participants, threshold, lib1, func(fid string, pid uint32, share []byte) {
		// store dealer share locally on node1 under dealer's node id
		n1.StoreDKGShare(fid, n1.nodeID, share)
	})
	if err != nil {
		t.Fatalf("Distribute failed: %v", err)
	}

	// Allow some time for peers to receive shares via libp2p
	time.Sleep(200 * time.Millisecond)

	// Try reconstructing on node2 by fetching shares from peers and local
	peersList := []uint32{1, 3}
	reconstructed, err := dkg.ReconstructFileKeyDistributed(context.Background(), fileID, peersList, threshold, lib2, func(fid string) ([]byte, bool) {
		return n2.GetLocalShare(fid)
	})
	if err != nil {
		t.Fatalf("Reconstruct failed: %v", err)
	}

	if string(reconstructed) != string(key) {
		t.Fatalf("reconstructed != original")
	}
}
