// Package compute provides the distributed compute orchestration layer.
//
// This package implements the "Manager" logic for the Distributed Compute System,
// following the Golden Rule: Go handles all networking and task orchestration.
//
// # Architecture
//
//	┌─────────────────────────────────────────────────────────────┐
//	│                     Go Orchestrator                          │
//	├─────────────────────────────────────────────────────────────┤
//	│  Manager        │ Scheduler       │ State                    │
//	│  ├─→ Delegate   │ ├─→ Complexity  │ ├─→ Job Tracking         │
//	│  ├─→ Execute    │ ├─→ Load Balance│ ├─→ Chunk Status         │
//	│  └─→ Merge      │ └─→ Routing     │ └─→ Worker Status        │
//	└─────────────────────────────────────────────────────────────┘
package compute

import (
	"context"
	"fmt"
	"sync"
	"time"
)

// ComputeConfig holds configuration for the compute service
type ComputeConfig struct {
	// MaxConcurrentJobs is the maximum number of jobs to process concurrently
	MaxConcurrentJobs int
	// DefaultTimeout is the default timeout for task execution
	DefaultTimeout time.Duration
	// RetryCount is the number of times to retry a failed task
	RetryCount int
	// ComplexityThreshold is the threshold above which tasks are delegated
	ComplexityThreshold float64
	// MinChunkSize is the minimum size for data chunks
	MinChunkSize int64
	// MaxChunkSize is the maximum size for data chunks
	MaxChunkSize int64
	// VerificationMode determines how results are verified
	VerificationMode VerificationMode
}

// DefaultConfig returns a default compute configuration
func DefaultConfig() ComputeConfig {
	return ComputeConfig{
		MaxConcurrentJobs:   10,
		DefaultTimeout:      5 * time.Minute,
		RetryCount:          3,
		ComplexityThreshold: 1.0,
		MinChunkSize:        64 * 1024,       // 64 KB
		MaxChunkSize:        1024 * 1024,     // 1 MB
		VerificationMode:    VerificationHash,
	}
}

// VerificationMode determines how task results are verified
type VerificationMode int

const (
	// VerificationNone skips verification
	VerificationNone VerificationMode = iota
	// VerificationHash verifies using SHA256 hash
	VerificationHash
	// VerificationMerkle verifies using Merkle tree proofs
	VerificationMerkle
	// VerificationRedundancy verifies by comparing results from multiple workers
	VerificationRedundancy
)

// TaskStatus represents the status of a compute task
type TaskStatus int

const (
	TaskPending TaskStatus = iota
	TaskAssigned
	TaskComputing
	TaskVerifying
	TaskCompleted
	TaskFailed
	TaskTimeout
	TaskCancelled
)

func (s TaskStatus) String() string {
	switch s {
	case TaskPending:
		return "pending"
	case TaskAssigned:
		return "assigned"
	case TaskComputing:
		return "computing"
	case TaskVerifying:
		return "verifying"
	case TaskCompleted:
		return "completed"
	case TaskFailed:
		return "failed"
	case TaskTimeout:
		return "timeout"
	case TaskCancelled:
		return "cancelled"
	default:
		return "unknown"
	}
}

// JobManifest describes a compute job
type JobManifest struct {
	// JobID is the unique identifier for this job
	JobID string `json:"jobId"`
	// WASMModule is the compiled WASM code
	WASMModule []byte `json:"wasmModule"`
	// InputData is the input data for the job
	InputData []byte `json:"inputData"`
	// SplitStrategy determines how data is split
	SplitStrategy string `json:"splitStrategy"`
	// MinChunkSize is the minimum chunk size
	MinChunkSize int64 `json:"minChunkSize"`
	// MaxChunkSize is the maximum chunk size
	MaxChunkSize int64 `json:"maxChunkSize"`
	// VerificationMode determines how results are verified
	VerificationMode VerificationMode `json:"verificationMode"`
	// TimeoutSecs is the timeout in seconds
	TimeoutSecs uint32 `json:"timeoutSecs"`
	// RetryCount is the number of retries
	RetryCount uint32 `json:"retryCount"`
	// Priority is the job priority (higher = more urgent)
	Priority uint32 `json:"priority"`
	// Redundancy is the number of workers to use for each task
	Redundancy uint32 `json:"redundancy"`
}

// ComputeTask represents a single compute task (a chunk of a job)
type ComputeTask struct {
	// TaskID is the unique identifier (jobId:chunkIndex)
	TaskID string `json:"taskId"`
	// ParentJobID is the parent job's ID
	ParentJobID string `json:"parentJobId"`
	// ChunkIndex is the index of this chunk
	ChunkIndex uint32 `json:"chunkIndex"`
	// WASMModule is the WASM code
	WASMModule []byte `json:"wasmModule"`
	// InputData is the input for this chunk
	InputData []byte `json:"inputData"`
	// FunctionName is the function to execute
	FunctionName string `json:"functionName"`
	// DelegationDepth is how many levels of delegation
	DelegationDepth uint32 `json:"delegationDepth"`
	// TimeoutMs is the timeout in milliseconds
	TimeoutMs uint64 `json:"timeoutMs"`
}

// TaskResult represents the result of a compute task
type TaskResult struct {
	// TaskID is the task identifier
	TaskID string `json:"taskId"`
	// Status is the task status
	Status TaskStatus `json:"status"`
	// ResultData is the result data
	ResultData []byte `json:"resultData"`
	// ResultHash is the SHA256 hash of the result
	ResultHash string `json:"resultHash"`
	// MerkleProof is the Merkle proof (if using Merkle verification)
	MerkleProof []string `json:"merkleProof,omitempty"`
	// ExecutionTimeMs is the execution time
	ExecutionTimeMs uint64 `json:"executionTimeMs"`
	// WorkerID is the ID of the worker that executed the task
	WorkerID string `json:"workerId"`
	// Error is the error message if failed
	Error string `json:"error,omitempty"`
}

// ChunkInfo describes a chunk of data
type ChunkInfo struct {
	// Index is the chunk index
	Index uint32 `json:"index"`
	// Size is the chunk size in bytes
	Size uint64 `json:"size"`
	// Hash is the SHA256 hash of the chunk
	Hash string `json:"hash"`
	// Status is the chunk status
	Status TaskStatus `json:"status"`
	// AssignedWorker is the assigned worker ID
	AssignedWorker string `json:"assignedWorker,omitempty"`
}

// JobStatus represents the status of a compute job
type JobStatus struct {
	// JobID is the job identifier
	JobID string `json:"jobId"`
	// Status is the overall job status
	Status TaskStatus `json:"status"`
	// Progress is the completion percentage (0.0 to 1.0)
	Progress float32 `json:"progress"`
	// CompletedChunks is the number of completed chunks
	CompletedChunks uint32 `json:"completedChunks"`
	// TotalChunks is the total number of chunks
	TotalChunks uint32 `json:"totalChunks"`
	// EstimatedTimeRemaining is the estimated time remaining in seconds
	EstimatedTimeRemaining uint32 `json:"estimatedTimeRemaining"`
	// Error is the error message if failed
	Error string `json:"error,omitempty"`
}

// ComputeCapacity represents a node's compute capacity
type ComputeCapacity struct {
	// CPUCores is the number of CPU cores
	CPUCores uint32 `json:"cpuCores"`
	// RAMMB is the available RAM in megabytes
	RAMMB uint64 `json:"ramMb"`
	// CurrentLoad is the current CPU load (0.0 to 1.0)
	CurrentLoad float32 `json:"currentLoad"`
	// DiskMB is the available disk space in megabytes
	DiskMB uint64 `json:"diskMb"`
	// BandwidthMbps is the network bandwidth in Mbps
	BandwidthMbps float32 `json:"bandwidthMbps"`
}

// Manager is the main orchestrator for distributed compute
type Manager struct {
	config   ComputeConfig
	jobs     map[string]*jobState
	workers  map[string]*workerState
	capacity ComputeCapacity
	mu       sync.RWMutex
	ctx      context.Context
	cancel   context.CancelFunc
}

// jobState tracks the internal state of a job
type jobState struct {
	manifest   *JobManifest
	chunks     []ChunkInfo
	results    map[uint32]*TaskResult
	status     TaskStatus
	startTime  time.Time
	lastUpdate time.Time
}

// workerState tracks the internal state of a worker
type workerState struct {
	id            string
	capacity      ComputeCapacity
	activeTasks   int
	lastSeen      time.Time
	trustScore    float32
	totalTasks    int
	successTasks  int
	avgExecutionMs float64
}

// NewManager creates a new compute manager
func NewManager(config ComputeConfig) *Manager {
	ctx, cancel := context.WithCancel(context.Background())
	
	return &Manager{
		config:   config,
		jobs:     make(map[string]*jobState),
		workers:  make(map[string]*workerState),
		capacity: probeCapacity(),
		ctx:      ctx,
		cancel:   cancel,
	}
}

// probeCapacity probes the system for compute capacity
func probeCapacity() ComputeCapacity {
	// In a real implementation, this would use sysinfo or similar
	return ComputeCapacity{
		CPUCores:      4,
		RAMMB:         8192,
		CurrentLoad:   0.1,
		DiskMB:        100000,
		BandwidthMbps: 100.0,
	}
}

// SubmitJob submits a new compute job
func (m *Manager) SubmitJob(manifest *JobManifest) (string, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	
	if manifest.JobID == "" {
		manifest.JobID = generateJobID()
	}
	
	// Check if job already exists
	if _, exists := m.jobs[manifest.JobID]; exists {
		return "", fmt.Errorf("job %s already exists", manifest.JobID)
	}
	
	// Create job state
	state := &jobState{
		manifest:   manifest,
		chunks:     []ChunkInfo{},
		results:    make(map[uint32]*TaskResult),
		status:     TaskPending,
		startTime:  time.Now(),
		lastUpdate: time.Now(),
	}
	
	m.jobs[manifest.JobID] = state
	
	// Start processing in background
	go m.processJob(manifest.JobID)
	
	return manifest.JobID, nil
}

// GetJobStatus returns the status of a job
func (m *Manager) GetJobStatus(jobID string) (*JobStatus, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	
	state, exists := m.jobs[jobID]
	if !exists {
		return nil, fmt.Errorf("job %s not found", jobID)
	}
	
	completed := uint32(0)
	for _, result := range state.results {
		if result.Status == TaskCompleted {
			completed++
		}
	}
	
	total := uint32(len(state.chunks))
	if total == 0 {
		total = 1
	}
	
	progress := float32(completed) / float32(total)
	
	return &JobStatus{
		JobID:                  jobID,
		Status:                 state.status,
		Progress:               progress,
		CompletedChunks:        completed,
		TotalChunks:            total,
		EstimatedTimeRemaining: m.estimateTimeRemaining(state, completed, total),
	}, nil
}

// GetJobResult returns the final result of a completed job
func (m *Manager) GetJobResult(jobID string, timeout time.Duration) ([]byte, error) {
	ctx, cancel := context.WithTimeout(m.ctx, timeout)
	defer cancel()
	
	// Wait for job to complete
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()
	
	for {
		select {
		case <-ctx.Done():
			return nil, fmt.Errorf("timeout waiting for job %s", jobID)
		case <-ticker.C:
			m.mu.RLock()
			state, exists := m.jobs[jobID]
			if !exists {
				m.mu.RUnlock()
				return nil, fmt.Errorf("job %s not found", jobID)
			}
			
			if state.status == TaskCompleted {
				// Merge results and return
				result := m.mergeResults(state)
				m.mu.RUnlock()
				return result, nil
			}
			
			if state.status == TaskFailed || state.status == TaskCancelled {
				m.mu.RUnlock()
				return nil, fmt.Errorf("job %s failed or was cancelled", jobID)
			}
			m.mu.RUnlock()
		}
	}
}

// CancelJob cancels a running job
func (m *Manager) CancelJob(jobID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	
	state, exists := m.jobs[jobID]
	if !exists {
		return fmt.Errorf("job %s not found", jobID)
	}
	
	state.status = TaskCancelled
	state.lastUpdate = time.Now()
	
	return nil
}

// GetCapacity returns this node's compute capacity
func (m *Manager) GetCapacity() ComputeCapacity {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.capacity
}

// RegisterWorker registers a new worker
func (m *Manager) RegisterWorker(workerID string, capacity ComputeCapacity) {
	m.mu.Lock()
	defer m.mu.Unlock()
	
	m.workers[workerID] = &workerState{
		id:         workerID,
		capacity:   capacity,
		lastSeen:   time.Now(),
		trustScore: 0.5, // Start with neutral trust
	}
}

// processJob processes a job (internal)
func (m *Manager) processJob(jobID string) {
	m.mu.Lock()
	state, exists := m.jobs[jobID]
	if !exists {
		m.mu.Unlock()
		return
	}
	
	state.status = TaskComputing
	manifest := state.manifest
	m.mu.Unlock()
	
	// Calculate complexity
	complexity := m.calculateComplexity(manifest)
	
	// Decide: delegate or execute locally
	if complexity > m.config.ComplexityThreshold && len(m.workers) > 0 {
		// Delegate to workers
		m.delegateJob(jobID, manifest)
	} else {
		// Execute locally
		m.executeJobLocally(jobID, manifest)
	}
}

// calculateComplexity calculates the complexity score for a job
func (m *Manager) calculateComplexity(manifest *JobManifest) float64 {
	dataFactor := float64(len(manifest.InputData)) / (1024.0 * 1024.0) // MB
	wasmFactor := float64(len(manifest.WASMModule)) / (64.0 * 1024.0)   // 64KB units
	
	return dataFactor * (1.0 + wasmFactor*0.1)
}

// delegateJob delegates a job to workers
func (m *Manager) delegateJob(jobID string, manifest *JobManifest) {
	// Split data into chunks
	chunks := m.splitData(manifest.InputData, manifest.MinChunkSize, manifest.MaxChunkSize)
	
	m.mu.Lock()
	state := m.jobs[jobID]
	state.chunks = make([]ChunkInfo, len(chunks))
	for i, chunk := range chunks {
		state.chunks[i] = ChunkInfo{
			Index:  uint32(i),
			Size:   uint64(len(chunk)),
			Hash:   hashData(chunk),
			Status: TaskPending,
		}
	}
	m.mu.Unlock()
	
	// Delegate chunks to workers
	var wg sync.WaitGroup
	for i, chunk := range chunks {
		wg.Add(1)
		go func(index int, data []byte, state *JobState) {
			defer wg.Done()
			m.executeChunk(jobID, uint32(index), manifest, data, state)
		}(i, chunk, state)
	}
	
	wg.Wait()
	
	// Check if all chunks completed
	m.mu.Lock()
	allComplete := true
	for _, result := range state.results {
		if result.Status != TaskCompleted {
			allComplete = false
			break
		}
	}
	
	if allComplete {
		state.status = TaskCompleted
	} else {
		state.status = TaskFailed
	}
	state.lastUpdate = time.Now()
	m.mu.Unlock()
}

// executeJobLocally executes a job on this node
func (m *Manager) executeJobLocally(jobID string, manifest *JobManifest) {
	// Create a single chunk for the entire job
	m.mu.Lock()
	state := m.jobs[jobID]
	state.chunks = []ChunkInfo{{
		Index:  0,
		Size:   uint64(len(manifest.InputData)),
		Hash:   hashData(manifest.InputData),
		Status: TaskPending,
	}}
	m.mu.Unlock()
	
	// Execute the chunk
	m.executeChunk(jobID, 0, manifest, manifest.InputData)
	
	// Mark job as complete
	m.mu.Lock()
	if result, ok := state.results[0]; ok && result.Status == TaskCompleted {
		state.status = TaskCompleted
	} else {
		state.status = TaskFailed
	}
	state.lastUpdate = time.Now()
	m.mu.Unlock()
}

// executeChunk executes a single chunk
func (m *Manager) executeChunk(jobID string, chunkIndex uint32, manifest *JobManifest, data []byte) {
	start := time.Now()
	
	// In a real implementation, this would call the Rust compute engine via IPC
	// For now, we simulate execution
	result := &TaskResult{
		TaskID:          fmt.Sprintf("%s:%d", jobID, chunkIndex),
		Status:          TaskCompleted,
		ResultData:      data, // Identity for simulation
		ResultHash:      hashData(data),
		ExecutionTimeMs: uint64(time.Since(start).Milliseconds()),
		WorkerID:        "local",
	}
	
	m.mu.Lock()
	state := m.jobs[jobID]
	state.results[chunkIndex] = result
	state.chunks[chunkIndex].Status = TaskCompleted
	state.lastUpdate = time.Now()
	m.mu.Unlock()
}

// splitData splits data into chunks
func (m *Manager) splitData(data []byte, minSize, maxSize int64) [][]byte {
	if len(data) == 0 {
		return [][]byte{}
	}
	
	// Calculate chunk size
	targetChunks := 8
	chunkSize := int64(len(data)) / int64(targetChunks)
	
	if chunkSize < minSize {
		chunkSize = minSize
	}
	if chunkSize > maxSize {
		chunkSize = maxSize
	}
	
	var chunks [][]byte
	for i := int64(0); i < int64(len(data)); i += chunkSize {
		end := i + chunkSize
		if end > int64(len(data)) {
			end = int64(len(data))
		}
		chunks = append(chunks, data[i:end])
	}
	
	return chunks
}

// mergeResults merges results from all chunks
func (m *Manager) mergeResults(state *jobState) []byte {
	// Sort results by chunk index and concatenate
	var result []byte
	for i := uint32(0); i < uint32(len(state.chunks)); i++ {
		if r, ok := state.results[i]; ok {
			result = append(result, r.ResultData...)
		}
	}
	return result
}

// estimateTimeRemaining estimates the remaining time for a job
func (m *Manager) estimateTimeRemaining(state *jobState, completed, total uint32) uint32 {
	if completed == 0 {
		return 0
	}
	
	elapsed := time.Since(state.startTime)
	avgPerChunk := elapsed / time.Duration(completed)
	remaining := total - completed
	
	return uint32(avgPerChunk.Seconds() * float64(remaining))
}

// Close shuts down the manager
func (m *Manager) Close() {
	m.cancel()
}

// generateJobID generates a unique job ID
func generateJobID() string {
	return fmt.Sprintf("job-%d", time.Now().UnixNano())
}

// hashData returns the SHA256 hash of data as a hex string
func hashData(data []byte) string {
	// In a real implementation, use crypto/sha256
	// For now, return a placeholder
	return fmt.Sprintf("%x", len(data))
}
