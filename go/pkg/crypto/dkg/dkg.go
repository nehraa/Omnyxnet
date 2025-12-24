package dkg

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
)

// NOTE: This is a simulated DKG module for testing and integration.
// It is NOT secure and should be replaced with a proper threshold
// cryptography implementation for production.

// RequestFileKey simulates a distributed key generation for a file.
// For tests, it deterministically derives a 32-byte key from the fileID.
func RequestFileKey(ctx context.Context, fileID string) ([]byte, error) {
	if fileID == "" {
		return nil, fmt.Errorf("fileID required")
	}
	// Derive key by hashing fileID and returning 32 bytes
	h := sha256.Sum256([]byte("dkg-filekey:" + fileID))
	key := make([]byte, 32)
	copy(key, h[:])
	return key, nil
}

// GenerateEphemeralKey generates a random 32-byte key for ephemeral jobs.
func GenerateEphemeralKey(ctx context.Context) ([]byte, error) {
	k := make([]byte, 32)
	if _, err := rand.Read(k); err != nil {
		return nil, err
	}
	return k, nil
}

// Debug helper: return hex of key
func KeyHex(b []byte) string {
	return hex.EncodeToString(b)
}
