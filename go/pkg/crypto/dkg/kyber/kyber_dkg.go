package kyberdkg

import (
	"context"
	"fmt"
	"sync"

	"go.dedis.ch/kyber/v3"
	"go.dedis.ch/kyber/v3/group/edwards25519"
	"go.dedis.ch/kyber/v3/util/random"
)

// Node represents a participant in the DKG protocol
type Node struct {
	ID   int
	Pri  kyber.Scalar // Private key share
	Pub  kyber.Point  // Public key share
	Priv kyber.Scalar // Long-term private key for signing
	Pub2 kyber.Point  // Long-term public key for verification
}

// Commit represents a public commitment in the Feldman/Pedersen VSS
type Commit struct {
	NodeID  int
	Degree  int
	C       []kyber.Point // Commitments to polynomial coefficients
	Proof   []byte        // Schnorr proof of knowledge
	Commits [][]byte      // Serialized commitments for easy transmission
}

// Share represents a secret share in the DKG protocol
type Share struct {
	FromID  int
	ToID    int
	Index   int
	S       kyber.Scalar
	Proof   []byte
	Payload []byte // Serialized share for transmission
}

// MessageType defines the message types in the DKG protocol
type MessageType int

const (
	// MessageCommitment: broadcast commitments in round 1
	MessageCommitment MessageType = iota
	// MessageShare: send secret shares in round 2
	MessageShare
	// MessageACK: acknowledge share receipt in round 3
	MessageACK
)

// Message wraps protocol messages
type Message struct {
	Type    MessageType
	FromID  int
	ToID    int
	Data    interface{}
	Payload []byte
}

// DKGState tracks state for a single DKG instance
type DKGState struct {
	NodeID       int
	Nodes        map[int]*Node
	Commits      map[int]*Commit // commitments from each node
	Shares       map[int]*Share  // shares received from each node
	Threshold    int
	n            kyber.Group
	suite        kyber.Group
	Coefficients []kyber.Scalar // polynomial coefficients for this node
	FinalKey     kyber.Scalar   // reconstructed final key share
	PublicKey    kyber.Point    // reconstructed public key
	mu           sync.RWMutex
}

// NewNode creates a new DKG participant with ephemeral keys
func NewNode(id int) *Node {
	suite := edwards25519.NewBlakeSHA256Ed25519()
	stream := random.New()
	priv := suite.Scalar().Pick(stream)
	pub := suite.Point().Mul(priv, nil)

	privLT := suite.Scalar().Pick(stream)
	pubLT := suite.Point().Mul(privLT, nil)

	return &Node{
		ID:   id,
		Pri:  priv,
		Pub:  pub,
		Priv: privLT,
		Pub2: pubLT,
	}
}

// NewDKGState initializes DKG state for a node
func NewDKGState(nodeID int, nodes []*Node, threshold int) *DKGState {
	suite := edwards25519.NewBlakeSHA256Ed25519()
	nodeMap := make(map[int]*Node)
	for _, n := range nodes {
		nodeMap[n.ID] = n
	}

	return &DKGState{
		NodeID:       nodeID,
		Nodes:        nodeMap,
		Commits:      make(map[int]*Commit),
		Shares:       make(map[int]*Share),
		Threshold:    threshold,
		n:            suite,
		suite:        suite,
		Coefficients: nil,
		FinalKey:     nil,
		PublicKey:    nil,
	}
}

// Round1GenerateCommitments generates commitments to polynomial coefficients (Feldman commitments)
func (s *DKGState) Round1GenerateCommitments() (*Commit, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	stream := random.New()

	// Generate polynomial coefficients: a0, a1, ..., a_{t-1}
	// where a0 is the secret to be shared
	coeffs := make([]kyber.Scalar, s.Threshold)
	for i := 0; i < s.Threshold; i++ {
		coeffs[i] = s.suite.Scalar().Pick(stream)
	}
	s.Coefficients = coeffs

	// Compute commitments to coefficients (public Feldman commitments)
	commits := make([]kyber.Point, s.Threshold)
	for i := 0; i < s.Threshold; i++ {
		commits[i] = s.suite.Point().Mul(coeffs[i], nil)
	}

	// Simple proof: serialize the commitment itself (minimal proof of knowledge)
	proof, err := commits[0].MarshalBinary()
	if err != nil {
		return nil, fmt.Errorf("marshal commit failed: %w", err)
	}

	// Serialize commits for transmission
	commitsPayload := make([][]byte, len(commits))
	for i, c := range commits {
		commitsPayload[i], err = c.MarshalBinary()
		if err != nil {
			return nil, fmt.Errorf("marshal commit failed: %w", err)
		}
	}

	return &Commit{
		NodeID:  s.NodeID,
		Degree:  s.Threshold,
		C:       commits,
		Proof:   proof,
		Commits: commitsPayload,
	}, nil
}

// Round2GenerateShares generates secret shares using Shamir's secret sharing over the polynomial
func (s *DKGState) Round2GenerateShares(commits map[int]*Commit) (map[int]*Share, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.Coefficients == nil {
		return nil, fmt.Errorf("coefficients not initialized")
	}

	// Store incoming commitments
	for id, commit := range commits {
		if commit != nil {
			s.Commits[id] = commit
		}
	}

	shares := make(map[int]*Share)
	numNodes := len(s.Nodes)

	// For each other node, compute a share: s_j = a_0 + a_1*j + a_2*j^2 + ... + a_{t-1}*j^{t-1}
	for j := 1; j <= numNodes; j++ {
		share := s.suite.Scalar().Zero()
		x := s.suite.Scalar().SetInt64(int64(j))
		xPower := s.suite.Scalar().One()

		for i := 0; i < s.Threshold; i++ {
			term := s.suite.Scalar().Mul(s.Coefficients[i], xPower)
			share = s.suite.Scalar().Add(share, term)
			xPower = s.suite.Scalar().Mul(xPower, x)
		}

		// Simple proof: serialize share itself (minimal proof)
		shareBytes, err := share.MarshalBinary()
		if err != nil {
			return nil, fmt.Errorf("marshal share failed: %w", err)
		}

		shares[j] = &Share{
			FromID:  s.NodeID,
			ToID:    j,
			Index:   j,
			S:       share,
			Proof:   shareBytes,
			Payload: shareBytes,
		}
	}

	return shares, nil
}

// Round3VerifyAndAccumulateShares verifies received shares against commitments and accumulates secret
func (s *DKGState) Round3VerifyAndAccumulateShares(sharesByID map[int]map[int]*Share) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	// Accumulate shares: x_i = sum of s_{j,i} for all j
	accumShare := s.suite.Scalar().Zero()

	var verified int
	for fromID, sharesFromNode := range sharesByID {
		share, exists := sharesFromNode[s.NodeID]
		if !exists {
			// This dealer didn't send us a share, skip (or mark as failure)
			continue
		}

		// Verify share against this dealer's commitments
		commit := s.Commits[fromID]
		if commit == nil {
			return fmt.Errorf("no commitment from dealer %d", fromID)
		}

		// Feldman verification: g^s_i should equal prod(C_k^{i^k})
		// where C_k are the commitments and s_i is the share for this node
		// This is equivalent to checking: s_i = a_0 + a_1*i + a_2*i^2 + ... (mod group order)
		// by verifying g^s_i == g^a_0 * (g^a_1)^i * (g^a_2)^{i^2} * ...

		x := s.suite.Scalar().SetInt64(int64(s.NodeID))
		xPower := s.suite.Scalar().One()
		expectedCommit := s.suite.Point().Null()

		for _, cCommit := range commit.C {
			term := s.suite.Point().Mul(xPower, cCommit)
			expectedCommit = s.suite.Point().Add(expectedCommit, term)
			xPower = s.suite.Scalar().Mul(xPower, x)
		}

		// Verify: g^share matches the expected commitment
		sharePoint := s.suite.Point().Mul(share.S, nil)
		if !sharePoint.Equal(expectedCommit) {
			return fmt.Errorf("share verification failed for dealer %d: expected %v, got %v", fromID, expectedCommit, sharePoint)
		}

		s.Shares[fromID] = share
		accumShare = s.suite.Scalar().Add(accumShare, share.S)
		verified++
	}

	if verified < s.Threshold {
		return fmt.Errorf("insufficient verified shares: %d < %d", verified, s.Threshold)
	}

	s.FinalKey = accumShare

	// Compute the public key by summing all commitments
	publicKey := s.suite.Point().Null()
	for _, commit := range s.Commits {
		if len(commit.C) > 0 {
			publicKey = s.suite.Point().Add(publicKey, commit.C[0])
		}
	}
	s.PublicKey = publicKey

	return nil
}

// RunDKG orchestrates the full Feldman/Pedersen DKG protocol
func RunDKG(ctx context.Context, nodes []*Node, threshold int, sendFunc func(from, to int, msg interface{}) error) ([][]byte, error) {
	if threshold > len(nodes) || threshold < 1 {
		return nil, fmt.Errorf("invalid threshold %d for %d nodes", threshold, len(nodes))
	}

	// Initialize state for each node
	states := make(map[int]*DKGState)
	for _, n := range nodes {
		states[n.ID] = NewDKGState(n.ID, nodes, threshold)
	}

	// Round 1: Generate commitments
	commits := make(map[int]*Commit)
	for _, n := range nodes {
		commit, err := states[n.ID].Round1GenerateCommitments()
		if err != nil {
			return nil, fmt.Errorf("round1 failed for node %d: %w", n.ID, err)
		}
		commits[n.ID] = commit
	}

	// Broadcast commitments to all nodes
	commitsMap := make(map[int]*Commit)
	for _, commit := range commits {
		commitsMap[commit.NodeID] = commit
	}

	// Round 2: Generate and exchange shares
	allShares := make(map[int]map[int]*Share)
	for _, n := range nodes {
		shares, err := states[n.ID].Round2GenerateShares(commitsMap)
		if err != nil {
			return nil, fmt.Errorf("round2 failed for node %d: %w", n.ID, err)
		}
		allShares[n.ID] = shares
	}

	// Reorganize shares: group by recipient
	sharesByRecipient := make(map[int]map[int]*Share)
	for nodeID := range states {
		sharesByRecipient[nodeID] = make(map[int]*Share)
	}
	for fromID, sharesMap := range allShares {
		for toID, share := range sharesMap {
			sharesByRecipient[toID][fromID] = share
		}
	}

	// Round 3: Verify and accumulate shares
	for _, n := range nodes {
		err := states[n.ID].Round3VerifyAndAccumulateShares(sharesByRecipient)
		if err != nil {
			return nil, fmt.Errorf("round3 failed for node %d: %w", n.ID, err)
		}
	}

	// Extract final secret key shares
	results := make([][]byte, len(nodes))
	for i, n := range nodes {
		keyBytes, err := states[n.ID].FinalKey.MarshalBinary()
		if err != nil {
			return nil, fmt.Errorf("marshal final key for node %d failed: %w", n.ID, err)
		}
		results[i] = keyBytes
	}

	return results, nil
}

// RecoverSecret recovers the shared secret from threshold shares using Lagrange interpolation
func RecoverSecret(suite kyber.Group, shares map[int]kyber.Scalar, threshold int) (kyber.Scalar, error) {
	if len(shares) < threshold {
		return nil, fmt.Errorf("insufficient shares: %d < %d", len(shares), threshold)
	}

	// Extract indices and shares
	indices := make([]int, 0)
	shareList := make([]kyber.Scalar, 0)
	for idx, share := range shares {
		indices = append(indices, idx)
		shareList = append(shareList, share)
	}

	// Use Lagrange interpolation at x=0
	secret := suite.Scalar().Zero()
	for i := 0; i < len(indices); i++ {
		xi := suite.Scalar().SetInt64(int64(indices[i]))
		numerator := suite.Scalar().One()
		denominator := suite.Scalar().One()

		for j := 0; j < len(indices); j++ {
			if i != j {
				xj := suite.Scalar().SetInt64(int64(indices[j]))
				numerator = suite.Scalar().Mul(numerator, suite.Scalar().Neg(xj))
				denominator = suite.Scalar().Mul(denominator, suite.Scalar().Sub(xi, xj))
			}
		}

		// li(0) = numerator / denominator
		lagrange := suite.Scalar().Mul(numerator, suite.Scalar().Inv(denominator))
		term := suite.Scalar().Mul(shareList[i], lagrange)
		secret = suite.Scalar().Add(secret, term)
	}

	return secret, nil
}

// VerifyRecovery verifies that recovered secret matches public key
func VerifyRecovery(suite kyber.Group, secret kyber.Scalar, publicKey kyber.Point) bool {
	recovered := suite.Point().Mul(secret, nil)
	return recovered.Equal(publicKey)
}
