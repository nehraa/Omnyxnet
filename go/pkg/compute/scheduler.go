// Package compute provides distributed compute orchestration
package compute

import (
	"sort"
	"sync"
	"time"
)

// Scheduler handles task scheduling and load balancing
type Scheduler struct {
	manager *Manager
	queue   []*scheduledTask
	mu      sync.Mutex
}

// scheduledTask represents a task in the scheduling queue
type scheduledTask struct {
	task       *ComputeTask
	priority   int
	complexity float64
	submitted  time.Time
	attempts   int
}

// NewScheduler creates a new scheduler
func NewScheduler(manager *Manager) *Scheduler {
	return &Scheduler{
		manager: manager,
		queue:   make([]*scheduledTask, 0),
	}
}

// Schedule adds a task to the scheduling queue
func (s *Scheduler) Schedule(task *ComputeTask, priority int) {
	s.mu.Lock()
	defer s.mu.Unlock()
	
	st := &scheduledTask{
		task:       task,
		priority:   priority,
		complexity: s.calculateTaskComplexity(task),
		submitted:  time.Now(),
		attempts:   0,
	}
	
	s.queue = append(s.queue, st)
	s.sortQueue()
}

// GetNextTask returns the next task to execute
func (s *Scheduler) GetNextTask() *ComputeTask {
	s.mu.Lock()
	defer s.mu.Unlock()
	
	if len(s.queue) == 0 {
		return nil
	}
	
	// Get highest priority task
	st := s.queue[0]
	s.queue = s.queue[1:]
	st.attempts++
	
	return st.task
}

// GetQueueLength returns the number of tasks in the queue
func (s *Scheduler) GetQueueLength() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return len(s.queue)
}

// sortQueue sorts the queue by priority (highest first) then by submission time
func (s *Scheduler) sortQueue() {
	sort.Slice(s.queue, func(i, j int) bool {
		if s.queue[i].priority != s.queue[j].priority {
			return s.queue[i].priority > s.queue[j].priority
		}
		return s.queue[i].submitted.Before(s.queue[j].submitted)
	})
}

// calculateTaskComplexity estimates the complexity of a task
func (s *Scheduler) calculateTaskComplexity(task *ComputeTask) float64 {
	dataFactor := float64(len(task.InputData)) / (1024.0 * 1024.0) // MB
	wasmFactor := float64(len(task.WASMModule)) / (64.0 * 1024.0)   // 64KB units
	
	return dataFactor * (1.0 + wasmFactor*0.1)
}

// SelectWorker selects the best worker for a task
func (s *Scheduler) SelectWorker(task *ComputeTask) string {
	s.manager.mu.RLock()
	defer s.manager.mu.RUnlock()
	
	if len(s.manager.workers) == 0 {
		return ""
	}
	
	var bestWorker string
	var bestScore float64 = -1
	
	for id, worker := range s.manager.workers {
		score := s.scoreWorker(worker, task)
		if score > bestScore {
			bestScore = score
			bestWorker = id
		}
	}
	
	return bestWorker
}

// scoreWorker calculates a score for a worker based on capacity and trust
func (s *Scheduler) scoreWorker(worker *workerState, task *ComputeTask) float64 {
	// Calculate availability score (1.0 = fully available, 0.0 = fully loaded)
	availScore := 1.0 - float64(worker.capacity.CurrentLoad)
	
	// Calculate trust score
	trustScore := float64(worker.trustScore)
	
	// Calculate recency score (prefer recently active workers)
	timeSinceLastSeen := time.Since(worker.lastSeen).Seconds()
	recencyScore := 1.0 / (1.0 + timeSinceLastSeen/60.0) // Decay over minutes
	
	// Weighted combination
	return availScore*0.4 + trustScore*0.4 + recencyScore*0.2
}

// UpdateWorkerLoad updates a worker's load
func (s *Scheduler) UpdateWorkerLoad(workerID string, load float32) {
	s.manager.mu.Lock()
	defer s.manager.mu.Unlock()
	
	if worker, exists := s.manager.workers[workerID]; exists {
		worker.capacity.CurrentLoad = load
		worker.lastSeen = time.Now()
	}
}

// UpdateWorkerTrust updates a worker's trust score based on task result
func (s *Scheduler) UpdateWorkerTrust(workerID string, success bool) {
	s.manager.mu.Lock()
	defer s.manager.mu.Unlock()
	
	worker, exists := s.manager.workers[workerID]
	if !exists {
		return
	}
	
	worker.totalTasks++
	if success {
		worker.successTasks++
	}
	
	// Exponential moving average
	oldScore := float64(worker.trustScore)
	if success {
		worker.trustScore = float32(oldScore*0.9 + 0.1) // Increase trust
	} else {
		worker.trustScore = float32(oldScore*0.9 + 0.0) // Decrease trust
	}
}

// GetLoadDistribution returns the current load distribution across workers
func (s *Scheduler) GetLoadDistribution() map[string]float32 {
	s.manager.mu.RLock()
	defer s.manager.mu.RUnlock()
	
	dist := make(map[string]float32)
	for id, worker := range s.manager.workers {
		dist[id] = worker.capacity.CurrentLoad
	}
	return dist
}

// RebalanceTasks redistributes tasks among workers
func (s *Scheduler) RebalanceTasks() {
	s.mu.Lock()
	defer s.mu.Unlock()
	
	// Re-sort queue based on current worker loads
	s.sortQueue()
}
