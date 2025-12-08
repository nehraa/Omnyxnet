package gradient

import (
	"fmt"
	"log"
	"sync"
	"time"
)

// GradientUpdate represents a gradient computation result from a worker
type GradientUpdate struct {
	WorkerID  uint32
	Loss      float64
	Timestamp time.Time
	Data      []float64
}

// Manager handles gradient aggregation and synchronization across workers
type Manager struct {
	mu               sync.RWMutex
	gradients        map[uint32]*GradientUpdate
	aggregationRound uint64
	lastAggregation  time.Time
}

// NewManager creates a new gradient manager
func NewManager() *Manager {
	return &Manager{
		gradients:       make(map[uint32]*GradientUpdate),
		lastAggregation: time.Now(),
	}
}

// SubmitGradient receives a gradient update from a worker
func (m *Manager) SubmitGradient(update *GradientUpdate) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.gradients[update.WorkerID] = update
	log.Printf("📊 Gradient received from worker %d (Loss: %.6f)", update.WorkerID, update.Loss)

	return nil
}

// AggregateGradients performs gradient aggregation across all submitted gradients
func (m *Manager) AggregateGradients() ([]float64, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if len(m.gradients) == 0 {
		log.Println("⚠️  No gradients available for aggregation")
		return nil, fmt.Errorf("no gradients available for aggregation")
	}

	// Average gradients from all workers
	var sumGradients []float64
	var expectedLength int
	count := 0

	for _, update := range m.gradients {
		if count == 0 {
			expectedLength = len(update.Data)
			sumGradients = make([]float64, expectedLength)
		} else if len(update.Data) != expectedLength {
			// Return error immediately on length mismatch for data consistency
			return nil, fmt.Errorf("gradient length mismatch: expected %d, got %d from worker %d",
				expectedLength, len(update.Data), update.WorkerID)
		}
		for i, v := range update.Data {
			sumGradients[i] += v
		}
		count++
	}

	if count == 0 {
		return nil, fmt.Errorf("no valid gradients to aggregate")
	}

	// Average
	for i := range sumGradients {
		sumGradients[i] /= float64(count)
	}

	m.aggregationRound++
	m.lastAggregation = time.Now()

	log.Printf("✅ Aggregated gradients from %d workers (Round: %d)", count, m.aggregationRound)

	return sumGradients, nil
}

// GetAggregationStats returns statistics about gradient aggregation
func (m *Manager) GetAggregationStats() map[string]interface{} {
	m.mu.RLock()
	defer m.mu.RUnlock()

	return map[string]interface{}{
		"aggregation_round":   m.aggregationRound,
		"last_aggregation":    m.lastAggregation,
		"active_workers":      len(m.gradients),
		"time_since_last_agg": time.Since(m.lastAggregation).Seconds(),
	}
}

// Reset clears all stored gradients for the next round
func (m *Manager) Reset() {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.gradients = make(map[uint32]*GradientUpdate)
	log.Println("🔄 Gradient manager reset for next round")
}
