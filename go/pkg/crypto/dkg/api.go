package dkg

import (
	"context"
	"fmt"
)

// DKGAdapter describes minimal network operations needed for dealer-based DKG
type DKGAdapter interface {
	SendShare(peerID uint32, fileID string, share []byte) error
	FetchShare(peerID uint32, fileID string) ([]byte, error)
}

// RequestFileKeyDistributed triggers a dealer-based DKG (Shamir dealer) for a file and returns the symmetric key.
// It distributes shares to participants and stores dealer's own share via the provided storeOwnShare callback.
func RequestFileKeyDistributed(ctx context.Context, fileID string, participants []uint32, threshold int, adapter DKGAdapter, storeOwnShare func(fileID string, peerID uint32, share []byte)) ([]byte, error) {
	if adapter == nil {
		return nil, fmt.Errorf("adapter required")
	}

	sendShare := func(pid uint32, fid string, share []byte) error {
		return adapter.SendShare(pid, fid, share)
	}

	return DistributeFileKey(ctx, fileID, participants, threshold, sendShare, storeOwnShare)
}

// ReconstructFileKeyDistributed reconstructs the key by fetching shares from peers (via adapter) and combining.
func ReconstructFileKeyDistributed(ctx context.Context, fileID string, peers []uint32, threshold int, adapter DKGAdapter, getLocalShare func(string) ([]byte, bool)) ([]byte, error) {
	if adapter == nil {
		return nil, fmt.Errorf("adapter required")
	}

	fetch := func(pid uint32, fid string) ([]byte, error) {
		return adapter.FetchShare(pid, fid)
	}

	return ReconstructKey(ctx, fileID, peers, threshold, fetch, getLocalShare)
}
