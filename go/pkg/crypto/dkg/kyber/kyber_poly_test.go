// Ultra-simple test to isolate the problem
package kyberdkg

import (
	"testing"

	"go.dedis.ch/kyber/v3/group/edwards25519"
	"go.dedis.ch/kyber/v3/util/random"
)

func TestPolyEvaluation(t *testing.T) {
	suite := edwards25519.NewBlakeSHA256Ed25519()
	_ = random.New() // unused for this test

	// Create polynomial: p(x) = 5 + 3x (using small constants for debugging)
	a0 := suite.Scalar().SetInt64(5)
	a1 := suite.Scalar().SetInt64(3)

	// Commitments: C_0 = g^5, C_1 = g^3
	C0 := suite.Point().Mul(a0, nil)
	C1 := suite.Point().Mul(a1, nil)

	// Share for x=2: p(2) = 5 + 3*2 = 11
	x := suite.Scalar().SetInt64(2)
	expectedShare := suite.Scalar().SetInt64(11)

	// Verify that g^11 == g^5 * (g^3)^2
	lhs := suite.Point().Mul(expectedShare, nil)

	// Compute RHS: C_0 * C_1^x
	xPower := suite.Scalar().SetInt64(1)
	rhs := suite.Point().Mul(xPower, C0) // C_0^1
	xPower = suite.Scalar().Mul(xPower, x)
	rhs = suite.Point().Add(rhs, suite.Point().Mul(xPower, C1)) // + C_1^x

	t.Logf("LHS (g^11): %x", lhs)
	t.Logf("RHS (C_0 * C_1^2): %x", rhs)

	if lhs.Equal(rhs) {
		t.Logf("PASS: g^11 == g^5 * (g^3)^2")
	} else {
		t.Errorf("FAIL: g^11 != g^5 * (g^3)^2")
	}
}
