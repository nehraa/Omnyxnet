package dkg

import (
	"context"
	"testing"
)

// Sanity test: ensure RequestFileKeyDistributed validates adapter argument
func TestRequestFileKeyDistributed_RequiresAdapter(t *testing.T) {
	_, err := RequestFileKeyDistributed(context.Background(), "fid", []uint32{1, 2}, 2, nil, nil)
	if err == nil {
		t.Fatalf("expected error when adapter is nil")
	}
}
