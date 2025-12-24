package dkg

import (
	"context"
	"testing"
)

func TestRequestFileKeyConsistency(t *testing.T) {
	ctx := context.Background()
	k1, err := RequestFileKey(ctx, "file-123")
	if err != nil {
		t.Fatalf("RequestFileKey failed: %v", err)
	}
	k2, err := RequestFileKey(ctx, "file-123")
	if err != nil {
		t.Fatalf("RequestFileKey failed: %v", err)
	}
	if string(k1) != string(k2) {
		t.Errorf("expected deterministic key but got different values")
	}
}

func TestGenerateEphemeralKeyUniqueness(t *testing.T) {
	ctx := context.Background()
	k1, err := GenerateEphemeralKey(ctx)
	if err != nil {
		t.Fatalf("GenerateEphemeralKey failed: %v", err)
	}
	k2, err := GenerateEphemeralKey(ctx)
	if err != nil {
		t.Fatalf("GenerateEphemeralKey failed: %v", err)
	}
	if string(k1) == string(k2) {
		t.Errorf("expected different ephemeral keys but got same")
	}
}
