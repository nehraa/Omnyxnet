package dkg

import (
	"context"
	"crypto/rand"
	"fmt"
	"time"

	vaultshamir "github.com/hashicorp/vault/shamir"
)

// Real (dealer-based) DKG using Shamir secret sharing and distribution to peers.
// NOTE: This is dealer-based (the requester acts as dealer). It uses real cryptographic
// secret sharing (Shamir) and network distribution of shares to peers. Production
// should move to dealerless threshold DKG (Feldman/VSS or dedicated DKG libs) when
// scaling beyond trusted-initiator flows.

// DistributeFileKey generates a random symmetric key for fileID, splits it with Shamir,
// sends shares to participants via the provided sendShare function, and stores own share
// by calling storeOwnShare. It returns the generated key for immediate use by the dealer.
func DistributeFileKey(ctx context.Context, fileID string, participants []uint32, threshold int, sendShare func(peerID uint32, fileID string, share []byte) error, storeOwnShare func(fileID string, peerID uint32, share []byte)) ([]byte, error) {
	if threshold <= 0 || threshold > len(participants) {
		return nil, fmt.Errorf("invalid threshold")
	}

	// Generate random 32-byte key
	key := make([]byte, 32)
	if _, err := rand.Read(key); err != nil {
		return nil, fmt.Errorf("failed to generate key: %w", err)
	}

	// Split into n shares
	n := len(participants)
	shares, err := vaultshamir.Split(key, n, threshold)
	if err != nil {
		return nil, fmt.Errorf("shamir split failed: %w", err)
	}

	// Distribute shares to participants
	for i, pid := range participants {
		share := shares[i]
		if pid == 0 {
			// invalid mapping
			continue
		}
		if err := sendShare(pid, fileID, share); err != nil {
			// best-effort: retry a few times
			attempts := 0
			for attempts < 3 {
				attempts++
				select {
				case <-ctx.Done():
					return nil, ctx.Err()
				case <-time.After(100 * time.Millisecond):
					if err2 := sendShare(pid, fileID, share); err2 == nil {
						break
					}
				}
			}
		}
		// If this is dealer's own share, store it locally via callback
		// Store even if send failed so dealer can reconstruct if necessary
		storeOwnShare(fileID, pid, share)
	}

	return key, nil
}

// ReconstructKey collects shares from peers using fetchShare and combines at least threshold shares.
func ReconstructKey(ctx context.Context, fileID string, peers []uint32, threshold int, fetchShare func(peerID uint32, fileID string) ([]byte, error), getLocalShare func(fileID string) ([]byte, bool)) ([]byte, error) {
	collected := make([][]byte, 0, threshold)
	// Try local share first
	if s, ok := getLocalShare(fileID); ok {
		collected = append(collected, s)
	}

	for _, pid := range peers {
		if len(collected) >= threshold {
			break
		}
		if pid == 0 {
			continue
		}
		sh, err := fetchShare(pid, fileID)
		if err != nil {
			// log and continue
			continue
		}
		if len(sh) == 0 {
			continue
		}
		collected = append(collected, sh)
	}

	if len(collected) < threshold {
		return nil, fmt.Errorf("insufficient shares: have %d, need %d", len(collected), threshold)
	}

	secret, err := vaultshamir.Combine(collected)
	if err != nil {
		return nil, fmt.Errorf("failed to combine shares: %w", err)
	}
	return secret, nil
}
