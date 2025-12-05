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
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"log"
	"math"
	"runtime"
	"sync"
	"time"
	"unsafe"
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
		ComplexityThreshold: 0.000001,    // Very low threshold to prefer delegation
		MinChunkSize:        1024,        // 1 KB - smaller chunks for testing
		MaxChunkSize:        1024 * 1024, // 1 MB
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

// TaskDelegator is an interface for sending tasks to remote workers
type TaskDelegator interface {
	// DelegateTask sends a task to a remote worker and returns the result
	DelegateTask(ctx context.Context, workerID string, task *ComputeTask) (*TaskResult, error)
	// GetAvailableWorkers returns a list of available worker IDs
	GetAvailableWorkers() []string
	// HasWorkers returns true if there are remote workers available
	HasWorkers() bool
}

// Manager is the main orchestrator for distributed compute
type Manager struct {
	config    ComputeConfig
	jobs      map[string]*jobState
	workers   map[string]*workerState
	capacity  ComputeCapacity
	delegator TaskDelegator
	mu        sync.RWMutex
	ctx       context.Context
	cancel    context.CancelFunc
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
	id             string
	capacity       ComputeCapacity
	activeTasks    int
	lastSeen       time.Time
	trustScore     float32
	totalTasks     int
	successTasks   int
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

// SetDelegator sets the task delegator for remote task execution
func (m *Manager) SetDelegator(delegator TaskDelegator) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.delegator = delegator
	log.Printf("⚙️ [COMPUTE] Task delegator configured")

}

// probeCapacity probes the system for compute capacity using actual system info
func probeCapacity() ComputeCapacity {
	numCPU := runtime.NumCPU()

	// Get memory stats
	var memStats runtime.MemStats
	runtime.ReadMemStats(&memStats)
	// Use total system memory approximated from heap stats
	// HeapSys is a rough approximation of available memory
	ramMB := memStats.HeapSys / (1024 * 1024)
	if ramMB < 512 {
		ramMB = 512 // Minimum reasonable value
	}

	// Estimate current load based on number of goroutines vs available CPUs
	numGoroutines := runtime.NumGoroutine()
	currentLoad := math.Min(float64(numGoroutines)/float64(numCPU*10), 1.0)

	return ComputeCapacity{
		CPUCores:      uint32(numCPU),
		RAMMB:         ramMB,
		CurrentLoad:   float32(currentLoad),
		DiskMB:        100000,       // Disk probing requires OS-specific code
		BandwidthMbps: 100.0,        // Network probing requires active measurement
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
	result, _, err := m.GetJobResultWithWorker(jobID, timeout)
	return result, err
}

// GetJobResultWithWorker returns the final result and the worker ID that executed the job
func (m *Manager) GetJobResultWithWorker(jobID string, timeout time.Duration) ([]byte, string, error) {
	ctx, cancel := context.WithTimeout(m.ctx, timeout)
	defer cancel()

	// Wait for job to complete
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return nil, "", fmt.Errorf("timeout waiting for job %s", jobID)
		case <-ticker.C:
			m.mu.RLock()
			state, exists := m.jobs[jobID]
			if !exists {
				m.mu.RUnlock()
				return nil, "", fmt.Errorf("job %s not found", jobID)
			}

			if state.status == TaskCompleted {
				// Merge results and get worker info
				result := m.mergeResults(state)

				// Get worker ID from first chunk result
				workerID := "local"
				for _, taskResult := range state.results {
					if taskResult != nil && taskResult.WorkerID != "" {
						workerID = taskResult.WorkerID
						break
					}
				}

				m.mu.RUnlock()
				return result, workerID, nil
			}

			if state.status == TaskFailed || state.status == TaskCancelled {
				m.mu.RUnlock()
				return nil, "", fmt.Errorf("job %s failed or was cancelled", jobID)
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
	delegator := m.delegator
	m.mu.Unlock()

	// Calculate complexity
	complexity := m.calculateComplexity(manifest)
	log.Printf("📊 [COMPUTE] Job %s complexity: %.4f (threshold: %.4f)", jobID, complexity, m.config.ComplexityThreshold)

	// Check if we have remote workers available
	// Primary: Use the delegator interface (libp2p peers) which is the recommended way
	// Fallback: Check manager's registered workers (for backwards compatibility or custom setups)
	hasRemoteWorkers := false
	if delegator != nil && delegator.HasWorkers() {
		// Delegator (libp2p) has connected peers - use this as primary source
		hasRemoteWorkers = true
		workers := delegator.GetAvailableWorkers()
		log.Printf("🌐 [COMPUTE] Delegator reports %d remote workers available for job %s", len(workers), jobID)
	} else if delegator == nil {
		// No delegator configured - check if workers were manually registered
		// This fallback supports test setups and custom worker registration
		m.mu.RLock()
		workerCount := len(m.workers)
		m.mu.RUnlock()
		if workerCount > 0 {
			hasRemoteWorkers = true
			log.Printf("🌐 [COMPUTE] Registered workers available for job %s: %d (no delegator)", jobID, workerCount)
		}
	}

	// Decide: delegate or execute locally
	// When remote workers are available, ALWAYS delegate to them for distributed computing
	// This ensures P2P distributed compute works as expected
	if hasRemoteWorkers {
		// Delegate to workers - this is the point of distributed compute!
		log.Printf("📤 [COMPUTE] Delegating job %s to remote workers (complexity: %.4f, threshold: %.4f)", jobID, complexity, m.config.ComplexityThreshold)
		m.delegateJob(jobID, manifest)
	} else {
		// No workers available, execute locally
		log.Printf("💻 [COMPUTE] No remote workers available, executing job %s locally (complexity: %.4f)", jobID, complexity)
		m.executeJobLocally(jobID, manifest)
	}
}

// calculateComplexity calculates the complexity score for a job
func (m *Manager) calculateComplexity(manifest *JobManifest) float64 {
	dataFactor := float64(len(manifest.InputData)) / (1024.0 * 1024.0) // MB
	wasmFactor := float64(len(manifest.WASMModule)) / (64.0 * 1024.0)  // 64KB units

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
	delegator := m.delegator
	m.mu.Unlock()

	// Get available workers
	var workers []string
	if delegator != nil && delegator.HasWorkers() {
		workers = delegator.GetAvailableWorkers()
		log.Printf("🌐 [COMPUTE] Found %d remote workers for job %s", len(workers), jobID)
	}

	// Delegate ALL chunks to remote workers for true distributed computing
	// Only fall back to local execution if no workers are available
	var wg sync.WaitGroup
	for i, chunk := range chunks {
		wg.Add(1)

		if len(workers) > 0 {
			// Delegate to remote worker using round-robin across available workers
			workerIdx := i % len(workers)
			workerID := workers[workerIdx]
			// Safe truncation of worker ID for logging
			shortID := workerID
			if len(workerID) > 12 {
				shortID = workerID[:12]
			}
			log.Printf("📤 [COMPUTE] Sending chunk %d to remote worker %s", i, shortID)
			go func(index int, data []byte, wID string, d TaskDelegator) {
				defer wg.Done()
				m.executeChunkRemote(jobID, uint32(index), manifest, data, wID, d)
			}(i, chunk, workerID, delegator)
		} else {
			// No remote workers, execute locally
			log.Printf("💻 [COMPUTE] No remote workers, executing chunk %d locally", i)
			go func(index int, data []byte) {
				defer wg.Done()
				m.executeChunk(jobID, uint32(index), manifest, data)
			}(i, chunk)
		}
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

	// Execute the actual compute operation
	resultData, err := executeMatrixBlockMultiply(data)

	var result *TaskResult
	if err != nil {
		log.Printf("❌ [COMPUTE] Chunk %d execution failed: %v", chunkIndex, err)
		result = &TaskResult{
			TaskID:          fmt.Sprintf("%s:%d", jobID, chunkIndex),
			Status:          TaskFailed,
			ResultData:      nil,
			ResultHash:      "",
			ExecutionTimeMs: uint64(time.Since(start).Milliseconds()),
			WorkerID:        "local",
			Error:           err.Error(),
		}
	} else {
		log.Printf("✅ [COMPUTE] Chunk %d completed locally: %d bytes → %d bytes",
			chunkIndex, len(data), len(resultData))
		result = &TaskResult{
			TaskID:          fmt.Sprintf("%s:%d", jobID, chunkIndex),
			Status:          TaskCompleted,
			ResultData:      resultData,
			ResultHash:      hashData(resultData),
			ExecutionTimeMs: uint64(time.Since(start).Milliseconds()),
			WorkerID:        "local",
		}
	}

	m.mu.Lock()
	state := m.jobs[jobID]
	state.results[chunkIndex] = result
	if result.Status == TaskCompleted {
		state.chunks[chunkIndex].Status = TaskCompleted
	} else {
		state.chunks[chunkIndex].Status = TaskFailed
	}
	state.lastUpdate = time.Now()
	m.mu.Unlock()
}

// executeChunkRemote executes a chunk on a remote worker
func (m *Manager) executeChunkRemote(jobID string, chunkIndex uint32, manifest *JobManifest, data []byte, workerID string, delegator TaskDelegator) {
	start := time.Now()

	log.Printf("📤 [COMPUTE] Delegating chunk %d to worker %s (%d bytes)",
		chunkIndex, workerID[:12], len(data))

	// Create compute task for remote execution
	task := &ComputeTask{
		TaskID:          fmt.Sprintf("%s:%d", jobID, chunkIndex),
		ParentJobID:     jobID,
		ChunkIndex:      chunkIndex,
		WASMModule:      manifest.WASMModule,
		InputData:       data,
		FunctionName:    "matrix_block_multiply",
		DelegationDepth: 0,
		TimeoutMs:       uint64(manifest.TimeoutSecs) * 1000,
	}

	// Execute on remote worker via delegator
	ctx, cancel := context.WithTimeout(m.ctx, time.Duration(manifest.TimeoutSecs)*time.Second)
	defer cancel()

	remoteResult, err := delegator.DelegateTask(ctx, workerID, task)

	var result *TaskResult
	if err != nil {
		log.Printf("❌ [COMPUTE] Remote chunk %d failed on %s: %v", chunkIndex, workerID[:12], err)
		// Fall back to local execution
		log.Printf("🔄 [COMPUTE] Falling back to local execution for chunk %d", chunkIndex)
		m.executeChunk(jobID, chunkIndex, manifest, data)
		return
	}

	if remoteResult.Status == TaskCompleted {
		log.Printf("✅ [COMPUTE] Chunk %d completed by worker %s in %dms: %d bytes",
			chunkIndex, workerID[:12], remoteResult.ExecutionTimeMs, len(remoteResult.ResultData))
		result = remoteResult
		result.WorkerID = workerID
	} else {
		log.Printf("❌ [COMPUTE] Remote chunk %d returned failure: %s", chunkIndex, remoteResult.Error)
		// Fall back to local execution
		log.Printf("🔄 [COMPUTE] Falling back to local execution for chunk %d", chunkIndex)
		m.executeChunk(jobID, chunkIndex, manifest, data)
		return
	}

	result.ExecutionTimeMs = uint64(time.Since(start).Milliseconds())

	m.mu.Lock()
	state := m.jobs[jobID]
	state.results[chunkIndex] = result
	if result.Status == TaskCompleted {
		state.chunks[chunkIndex].Status = TaskCompleted
	} else {
		state.chunks[chunkIndex].Status = TaskFailed
	}
	state.lastUpdate = time.Now()
	m.mu.Unlock()
}

// ExecuteMatrixBlockMultiply executes matrix block multiplication (exported for compute protocol)
// Input format: [a_rows:4][a_cols:4][a_data:a_rows*a_cols*8][b_rows:4][b_cols:4][b_data:b_rows*b_cols*8]
// Output format: [c_rows:4][c_cols:4][c_data:c_rows*c_cols*8]
func ExecuteMatrixBlockMultiply(data []byte) ([]byte, error) {
	return executeMatrixBlockMultiply(data)
}

// executeMatrixBlockMultiply executes matrix block multiplication
// Input format: [a_rows:4][a_cols:4][a_data:a_rows*a_cols*8][b_rows:4][b_cols:4][b_data:b_rows*b_cols*8]
// Output format: [c_rows:4][c_cols:4][c_data:c_rows*c_cols*8]
func executeMatrixBlockMultiply(data []byte) ([]byte, error) {
	if len(data) < 16 {
		return nil, fmt.Errorf("input data too short: %d bytes", len(data))
	}

	// Debug: print first 16 bytes
	log.Printf("   📊 [COMPUTE] Data length: %d, first 16 bytes: %x", len(data), data[:16])

	// Parse matrix A dimensions (big-endian)
	aRows := uint32(data[0])<<24 | uint32(data[1])<<16 | uint32(data[2])<<8 | uint32(data[3])
	aCols := uint32(data[4])<<24 | uint32(data[5])<<16 | uint32(data[6])<<8 | uint32(data[7])

	log.Printf("   📊 [COMPUTE] Parsed dimensions: aRows=%d, aCols=%d", aRows, aCols)

	// Check for integer overflow before multiplication: aRows * aCols * 8
	// Maximum safe value: math.MaxInt / 8 to prevent overflow when multiplied by 8
	const maxMatrixElements = math.MaxInt32 / 8
	if uint64(aRows)*uint64(aCols) > maxMatrixElements {
		return nil, fmt.Errorf("matrix A dimensions too large: %d x %d would overflow", aRows, aCols)
	}

	aDataSize := int(aRows * aCols * 8)
	if len(data) < 8+aDataSize+8 {
		return nil, fmt.Errorf("input data incomplete for matrix A: need %d, have %d", 8+aDataSize+8, len(data))
	}

	// Parse matrix B dimensions
	bOffset := 8 + aDataSize
	bRows := uint32(data[bOffset])<<24 | uint32(data[bOffset+1])<<16 | uint32(data[bOffset+2])<<8 | uint32(data[bOffset+3])
	bCols := uint32(data[bOffset+4])<<24 | uint32(data[bOffset+5])<<16 | uint32(data[bOffset+6])<<8 | uint32(data[bOffset+7])

	// Check for integer overflow before multiplication: bRows * bCols * 8
	if uint64(bRows)*uint64(bCols) > maxMatrixElements {
		return nil, fmt.Errorf("matrix B dimensions too large: %d x %d would overflow", bRows, bCols)
	}

	bDataSize := int(bRows * bCols * 8)
	if len(data) < bOffset+8+bDataSize {
		return nil, fmt.Errorf("input data incomplete for matrix B")
	}

	// Validate dimensions for matrix multiplication
	if aCols != bRows {
		return nil, fmt.Errorf("matrix dimensions incompatible: %dx%d * %dx%d", aRows, aCols, bRows, bCols)
	}

	log.Printf("   📊 [COMPUTE] Multiplying %dx%d * %dx%d matrices", aRows, aCols, bRows, bCols)

	// Read matrix A data
	matrixA := make([][]float64, aRows)
	offset := 8
	for i := uint32(0); i < aRows; i++ {
		matrixA[i] = make([]float64, aCols)
		for j := uint32(0); j < aCols; j++ {
			bits := uint64(data[offset])<<56 | uint64(data[offset+1])<<48 |
				uint64(data[offset+2])<<40 | uint64(data[offset+3])<<32 |
				uint64(data[offset+4])<<24 | uint64(data[offset+5])<<16 |
				uint64(data[offset+6])<<8 | uint64(data[offset+7])
			matrixA[i][j] = float64frombits(bits)
			offset += 8
		}
	}

	// Debug: print first element
	log.Printf("   📊 [COMPUTE] Matrix A[0][0] = %f", matrixA[0][0])

	// Read matrix B data
	matrixB := make([][]float64, bRows)
	offset = bOffset + 8
	for i := uint32(0); i < bRows; i++ {
		matrixB[i] = make([]float64, bCols)
		for j := uint32(0); j < bCols; j++ {
			bits := uint64(data[offset])<<56 | uint64(data[offset+1])<<48 |
				uint64(data[offset+2])<<40 | uint64(data[offset+3])<<32 |
				uint64(data[offset+4])<<24 | uint64(data[offset+5])<<16 |
				uint64(data[offset+6])<<8 | uint64(data[offset+7])
			matrixB[i][j] = float64frombits(bits)
			offset += 8
		}
	}

	// Debug: print first element of B
	log.Printf("   📊 [COMPUTE] Matrix B[0][0] = %f", matrixB[0][0])

	// Perform matrix multiplication: C = A * B
	cRows := aRows
	cCols := bCols
	matrixC := make([][]float64, cRows)
	for i := uint32(0); i < cRows; i++ {
		matrixC[i] = make([]float64, cCols)
		for j := uint32(0); j < cCols; j++ {
			sum := 0.0
			for k := uint32(0); k < aCols; k++ {
				sum += matrixA[i][k] * matrixB[k][j]
			}
			matrixC[i][j] = sum
		}
	}

	// Serialize result matrix
	resultSize := 8 + int(cRows*cCols*8)
	result := make([]byte, resultSize)

	// Write dimensions (big-endian)
	result[0] = byte(cRows >> 24)
	result[1] = byte(cRows >> 16)
	result[2] = byte(cRows >> 8)
	result[3] = byte(cRows)
	result[4] = byte(cCols >> 24)
	result[5] = byte(cCols >> 16)
	result[6] = byte(cCols >> 8)
	result[7] = byte(cCols)

	// Write matrix data
	offset = 8
	for i := uint32(0); i < cRows; i++ {
		for j := uint32(0); j < cCols; j++ {
			bits := float64bits(matrixC[i][j])
			result[offset] = byte(bits >> 56)
			result[offset+1] = byte(bits >> 48)
			result[offset+2] = byte(bits >> 40)
			result[offset+3] = byte(bits >> 32)
			result[offset+4] = byte(bits >> 24)
			result[offset+5] = byte(bits >> 16)
			result[offset+6] = byte(bits >> 8)
			result[offset+7] = byte(bits)
			offset += 8
		}
	}

	return result, nil
}

// float64frombits converts bits to float64
func float64frombits(bits uint64) float64 {
	return *(*float64)(unsafe.Pointer(&bits))
}

// float64bits converts float64 to bits
func float64bits(f float64) uint64 {
	return *(*uint64)(unsafe.Pointer(&f))
}

// splitData splits data into chunks
func (m *Manager) splitData(data []byte, minSize, maxSize int64) [][]byte {
	if len(data) == 0 {
		return [][]byte{}
	}

	// For matrix multiplication data (which has a specific header structure),
	// arbitrary splitting will break the format.
	// If the data fits within MaxChunkSize, keep it as one chunk.
	// This ensures the worker receives the full matrix problem.
	if int64(len(data)) <= maxSize {
		return [][]byte{data}
	}

	// If we MUST split (data > MaxChunkSize), we use the max size.
	// Note: This will still break matrix multiplication if the logic isn't
	// matrix-aware, but it's better than forcing small chunks.
	chunkSize := maxSize

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
	hash := sha256.Sum256(data)
	return hex.EncodeToString(hash[:])
}
