package main

import (
	"context"
	"testing"

	"github.com/pangea-net/go-node/pkg/crypto/dkg"
)

func TestCESPipelineWithDKGKey(t *testing.T) {
	ctx := context.Background()
	fileKey, err := dkg.RequestFileKey(ctx, "test-file-xyz")
	if err != nil {
		t.Fatalf("RequestFileKey failed: %v", err)
	}
	var keyArr [32]byte
	copy(keyArr[:], fileKey)

	pipeline := NewCESPipelineWithKey(1, keyArr) // low compression for test
	if pipeline == nil {
		t.Fatalf("Failed to create CES pipeline with key")
	}
	defer pipeline.Close()

	input := []byte("hello world - CES with DKG key")
	shards, err := pipeline.Process(input)
	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	present := make([]bool, len(shards))
	for i := range present {
		present[i] = true
	}

	reconstructed, err := pipeline.Reconstruct(shards, present)
	if err != nil {
		t.Fatalf("Reconstruct failed: %v", err)
	}

	if string(reconstructed) != string(input) {
		t.Fatalf("Reconstructed mismatch: got %s want %s", string(reconstructed), string(input))
	}
}
