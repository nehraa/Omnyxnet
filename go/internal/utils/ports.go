package utils

import (
	"fmt"
	"net"
	"time"
)

// CheckPortAvailable checks if a port is available for binding
func CheckPortAvailable(addr string) error {
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		return fmt.Errorf("port %s is not available: %w", addr, err)
	}
	ln.Close()
	return nil
}

// WaitForPort waits for a port to become available (for cleanup scenarios)
func WaitForPort(addr string, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		if err := CheckPortAvailable(addr); err == nil {
			return nil
		}
		time.Sleep(100 * time.Millisecond)
	}
	return fmt.Errorf("port %s did not become available within %v", addr, timeout)
}

// CleanupPort attempts to free a port by checking if it's in use
// This is a best-effort cleanup - actual port cleanup happens when connections close
func CleanupPort(addr string) error {
	// Check if port is already available
	if err := CheckPortAvailable(addr); err == nil {
		return nil // Port is already free
	}

	// Try to connect to see if something is listening
	conn, err := net.DialTimeout("tcp", addr, 100*time.Millisecond)
	if err == nil {
		conn.Close()
		return fmt.Errorf("port %s is in use by another process", addr)
	}

	// Port might be in TIME_WAIT state, wait a bit
	return WaitForPort(addr, 2*time.Second)
}
