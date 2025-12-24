// Test Feldman VSS verification directly
package kyberdkg

import (
	"testing"

	"go.dedis.ch/kyber/v3"
	"go.dedis.ch/kyber/v3/group/edwards25519"
	"go.dedis.ch/kyber/v3/util/random"
)

func TestFeldmanDirectVerification(t *testing.T) {
	suite := edwards25519.NewBlakeSHA256Ed25519()
	stream := random.New()

	// Create a simple polynomial: p(x) = a0 + a1*x
	a0 := suite.Scalar().Pick(stream)
	a1 := suite.Scalar().Pick(stream)

	// Commitments
	C0 := suite.Point().Mul(a0, nil)
	C1 := suite.Point().Mul(a1, nil)

	// Evaluate at x=2: p(2) = a0 + 2*a1
	x := suite.Scalar().SetInt64(2)
	s_2 := suite.Scalar().Add(a0, suite.Scalar().Mul(a1, x))

	// Verify: g^s_2 should equal C0 * C1^2
	lhs := suite.Point().Mul(s_2, nil)

	// Compute RHS: C0 * C1^2
	C1_pow_x := suite.Point().Mul(x, C1)
	rhs := suite.Point().Add(C0, C1_pow_x)

	t.Logf("LHS (g^s_2): %x", lhs)
	t.Logf("RHS (C0 * C1^x): %x", rhs)

	if !lhs.Equal(rhs) {
		t.Errorf("verification failed: LHS != RHS")
	} else {
		t.Logf("Direct Feldman verification PASSED")
	}
}

func TestFeldmanMultiRound(t *testing.T) {
	suite := edwards25519.NewBlakeSHA256Ed25519()
	stream := random.New()

	// Dealer creates polynomial: p(x) = a0 + a1*x + a2*x^2
	threshold := 3
	coeffs := make([]kyber.Scalar, threshold)
	for i := 0; i < threshold; i++ {
		coeffs[i] = suite.Scalar().Pick(stream)
	}

	// Commitments
	commits := make([]kyber.Point, threshold)
	for i := 0; i < threshold; i++ {
		commits[i] = suite.Point().Mul(coeffs[i], nil)
	}

	// Evaluate share for participant i=1
	i := suite.Scalar().SetInt64(1)
	share := suite.Scalar().Zero()
	iPower := suite.Scalar().One()
	for j := 0; j < threshold; j++ {
		term := suite.Scalar().Mul(coeffs[j], iPower)
		share = suite.Scalar().Add(share, term)
		iPower = suite.Scalar().Mul(iPower, i)
	}

	// Verify share: g^share should equal C0 * C1^i * C2^{i^2}
	lhs := suite.Point().Mul(share, nil)

	rhs := suite.Point().Null()
	iPower = suite.Scalar().One()
	for _, commit := range commits {
		term := suite.Point().Mul(iPower, commit)
		rhs = suite.Point().Add(rhs, term)
		iPower = suite.Scalar().Mul(iPower, i)
	}

	t.Logf("Share g^s: %x", lhs)
	t.Logf("Product: %x", rhs)

	if !lhs.Equal(rhs) {
		t.Errorf("multi-round verification failed")
	} else {
		t.Logf("Multi-round Feldman verification PASSED")
	}
}
