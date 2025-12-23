package main

import (
	"log"
	"runtime"
	"time"
)

// NetworkMetricsCollector collects network and system metrics
type NetworkMetricsCollector struct {
	store   *NodeStore
	network NetworkAdapter
}

// NewMetricsCollector creates a new metrics collector
func NewMetricsCollector(store *NodeStore, network NetworkAdapter) *NetworkMetricsCollector {
	return &NetworkMetricsCollector{
		store:   store,
		network: network,
	}
}

// CollectMetrics gathers current network and system metrics
func (c *NetworkMetricsCollector) CollectMetrics() (avgRTT, packetLoss, bandwidth float32, peerCount uint32, cpuUsage, ioCapacity float32) {
	// 1. Get peer count
	peerIDs := c.network.GetConnectedPeers()
	peerCount = uint32(len(peerIDs))

	// 2. Calculate average RTT and packet loss
	totalRTT := float32(0.0)
	totalPacketLoss := float32(0.0)
	validPeers := 0

	for _, peerID := range peerIDs {
		latency, _, loss, err := c.network.GetConnectionQuality(peerID)
		if err == nil {
			totalRTT += latency
			totalPacketLoss += loss
			validPeers++
		}
	}

	if validPeers > 0 {
		avgRTT = totalRTT / float32(validPeers)
		packetLoss = totalPacketLoss / float32(validPeers)
	}

	// 3. Estimate bandwidth (simplified - would need actual measurement)
	// For now, use a heuristic based on RTT
	if avgRTT < 10 {
		bandwidth = 1000.0 // High-speed local network
	} else if avgRTT < 50 {
		bandwidth = 100.0 // Good broadband
	} else if avgRTT < 200 {
		bandwidth = 10.0 // Average broadband
	} else {
		bandwidth = 1.0 // Slow connection
	}

	// 4. Get CPU usage
	cpuUsage = getCPUUsage()

	// 5. Estimate I/O capacity (simplified)
	// This would ideally measure actual disk I/O performance
	ioCapacity = 0.8 // Default to 80% capacity

	return
}

// getCPUUsage returns estimated CPU usage (0.0 to 1.0)
func getCPUUsage() float32 {
	var m runtime.MemStats
	runtime.ReadMemStats(&m)

	// This is a simplified metric
	// In production, you'd want to use a proper CPU monitoring library
	numGoroutines := float32(runtime.NumGoroutine())
	numCPU := float32(runtime.NumCPU())

	// Rough estimate: usage = goroutines / (cpus * 100)
	usage := numGoroutines / (numCPU * 100.0)
	if usage > 1.0 {
		usage = 1.0
	}

	return usage
}

// MonitorMetrics continuously monitors and logs metrics
func (c *NetworkMetricsCollector) MonitorMetrics(interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for range ticker.C {
		avgRTT, packetLoss, bandwidth, peerCount, cpuUsage, ioCapacity := c.CollectMetrics()

		log.Printf("📊 Network Metrics: RTT=%.1fms, Loss=%.2f%%, BW=%.1fMbps, Peers=%d, CPU=%.1f%%, I/O=%.1f%%",
			avgRTT, packetLoss*100, bandwidth, peerCount, cpuUsage*100, ioCapacity*100)
	}
}
