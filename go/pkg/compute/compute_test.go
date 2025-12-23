package compute

import (
	"context"
	"sync/atomic"
	"testing"
	"time"
)

func TestNewManager(t *testing.T) {
	config := DefaultConfig()
	manager := NewManager(config)

	if manager == nil {
		t.Fatal("NewManager returned nil")
	}

	defer manager.Close()
}

func TestSubmitJob(t *testing.T) {
	config := DefaultConfig()
	manager := NewManager(config)
	defer manager.Close()

	manifest := &JobManifest{
		JobID:            "test-job-1",
		WASMModule:       []byte("test-wasm"),
		InputData:        []byte("test input data for processing"),
		SplitStrategy:    "fixed_size",
		MinChunkSize:     1024,
		MaxChunkSize:     65536,
		VerificationMode: VerificationHash,
		TimeoutSecs:      60,
		RetryCount:       3,
		Priority:         5,
		Redundancy:       1,
	}

	jobID, err := manager.SubmitJob(manifest)
	if err != nil {
		t.Fatalf("SubmitJob failed: %v", err)
	}

	if jobID != "test-job-1" {
		t.Errorf("Expected job ID 'test-job-1', got '%s'", jobID)
	}

	// Submit same job again should fail
	_, err = manager.SubmitJob(manifest)
	if err == nil {
		t.Error("Expected error when submitting duplicate job")
	}
}

func TestGetJobStatus(t *testing.T) {
	config := DefaultConfig()
	manager := NewManager(config)
	defer manager.Close()

	manifest := &JobManifest{
		JobID:     "status-test-job",
		InputData: []byte("test data"),
	}

	_, err := manager.SubmitJob(manifest)
	if err != nil {
		t.Fatalf("SubmitJob failed: %v", err)
	}

	// Wait a bit for job to start processing
	time.Sleep(50 * time.Millisecond)

	status, err := manager.GetJobStatus("status-test-job")
	if err != nil {
		t.Fatalf("GetJobStatus failed: %v", err)
	}

	if status.JobID != "status-test-job" {
		t.Errorf("Expected job ID 'status-test-job', got '%s'", status.JobID)
	}
}

func TestGetJobStatusNotFound(t *testing.T) {
	config := DefaultConfig()
	manager := NewManager(config)
	defer manager.Close()

	_, err := manager.GetJobStatus("non-existent-job")
	if err == nil {
		t.Error("Expected error for non-existent job")
	}
}

func TestCancelJob(t *testing.T) {
	config := DefaultConfig()
	manager := NewManager(config)
	defer manager.Close()

	manifest := &JobManifest{
		JobID:     "cancel-test-job",
		InputData: []byte("test data"),
	}

	_, err := manager.SubmitJob(manifest)
	if err != nil {
		t.Fatalf("SubmitJob failed: %v", err)
	}

	err = manager.CancelJob("cancel-test-job")
	if err != nil {
		t.Fatalf("CancelJob failed: %v", err)
	}

	status, err := manager.GetJobStatus("cancel-test-job")
	if err != nil {
		t.Fatalf("GetJobStatus failed: %v", err)
	}

	if status.Status != TaskCancelled {
		t.Errorf("Expected status TaskCancelled, got %v", status.Status)
	}
}

func TestGetCapacity(t *testing.T) {
	config := DefaultConfig()
	manager := NewManager(config)
	defer manager.Close()

	capacity := manager.GetCapacity()

	if capacity.CPUCores == 0 {
		t.Error("Expected non-zero CPU cores")
	}

	if capacity.RAMMB == 0 {
		t.Error("Expected non-zero RAM")
	}
}

func TestRegisterWorker(t *testing.T) {
	config := DefaultConfig()
	manager := NewManager(config)
	defer manager.Close()

	capacity := ComputeCapacity{
		CPUCores:      8,
		RAMMB:         16384,
		CurrentLoad:   0.2,
		DiskMB:        500000,
		BandwidthMbps: 1000.0,
	}

	manager.RegisterWorker("worker-1", capacity)

	// Verify worker was registered
	manager.mu.RLock()
	_, exists := manager.workers["worker-1"]
	manager.mu.RUnlock()

	if !exists {
		t.Error("Worker was not registered")
	}
}

func TestTaskStatusString(t *testing.T) {
	tests := []struct {
		status   TaskStatus
		expected string
	}{
		{TaskPending, "pending"},
		{TaskAssigned, "assigned"},
		{TaskComputing, "computing"},
		{TaskVerifying, "verifying"},
		{TaskCompleted, "completed"},
		{TaskFailed, "failed"},
		{TaskTimeout, "timeout"},
		{TaskCancelled, "cancelled"},
	}

	for _, tt := range tests {
		if got := tt.status.String(); got != tt.expected {
			t.Errorf("TaskStatus.String() = %v, want %v", got, tt.expected)
		}
	}
}

func TestSplitData(t *testing.T) {
	config := DefaultConfig()
	manager := NewManager(config)
	defer manager.Close()

	// Create 100KB of test data
	data := make([]byte, 100*1024)
	for i := range data {
		data[i] = byte(i % 256)
	}

	chunks := manager.splitData(data, 10*1024, 50*1024)

	if len(chunks) == 0 {
		t.Error("Expected at least one chunk")
	}

	// Verify all data is preserved
	var reassembled []byte
	for _, chunk := range chunks {
		reassembled = append(reassembled, chunk...)
	}

	if len(reassembled) != len(data) {
		t.Errorf("Data size mismatch: got %d, want %d", len(reassembled), len(data))
	}

	for i := range data {
		if data[i] != reassembled[i] {
			t.Errorf("Data mismatch at position %d", i)
			break
		}
	}
}

func TestDefaultConfig(t *testing.T) {
	config := DefaultConfig()

	if config.MaxConcurrentJobs <= 0 {
		t.Error("MaxConcurrentJobs should be positive")
	}

	if config.DefaultTimeout <= 0 {
		t.Error("DefaultTimeout should be positive")
	}

	if config.RetryCount < 0 {
		t.Error("RetryCount should be non-negative")
	}

	if config.MinChunkSize <= 0 {
		t.Error("MinChunkSize should be positive")
	}

	if config.MaxChunkSize < config.MinChunkSize {
		t.Error("MaxChunkSize should be >= MinChunkSize")
	}
}

func TestScheduler(t *testing.T) {
	config := DefaultConfig()
	manager := NewManager(config)
	defer manager.Close()

	scheduler := NewScheduler(manager)

	// Add some tasks
	task1 := &ComputeTask{
		TaskID:      "task-1",
		ParentJobID: "job-1",
		ChunkIndex:  0,
		InputData:   []byte("task 1 data"),
	}

	task2 := &ComputeTask{
		TaskID:      "task-2",
		ParentJobID: "job-1",
		ChunkIndex:  1,
		InputData:   []byte("task 2 data - higher priority"),
	}

	// Schedule with different priorities
	scheduler.Schedule(task1, 5)
	scheduler.Schedule(task2, 10) // Higher priority

	// Higher priority task should come first
	next := scheduler.GetNextTask()
	if next.TaskID != "task-2" {
		t.Errorf("Expected task-2 (higher priority), got %s", next.TaskID)
	}

	// Then lower priority
	next = scheduler.GetNextTask()
	if next.TaskID != "task-1" {
		t.Errorf("Expected task-1, got %s", next.TaskID)
	}

	// Queue should be empty
	next = scheduler.GetNextTask()
	if next != nil {
		t.Error("Expected nil, queue should be empty")
	}
}

func TestSchedulerSelectWorker(t *testing.T) {
	config := DefaultConfig()
	manager := NewManager(config)
	defer manager.Close()

	scheduler := NewScheduler(manager)

	// Register some workers
	manager.RegisterWorker("worker-1", ComputeCapacity{
		CPUCores:    4,
		RAMMB:       8192,
		CurrentLoad: 0.9, // High load
	})

	manager.RegisterWorker("worker-2", ComputeCapacity{
		CPUCores:    8,
		RAMMB:       16384,
		CurrentLoad: 0.1, // Low load
	})

	task := &ComputeTask{
		TaskID:    "test-task",
		InputData: []byte("test"),
	}

	selected := scheduler.SelectWorker(task)

	// Should select worker-2 (lower load)
	if selected != "worker-2" {
		t.Errorf("Expected worker-2 (lower load), got %s", selected)
	}
}

func TestSchedulerUpdateWorkerTrust(t *testing.T) {
	config := DefaultConfig()
	manager := NewManager(config)
	defer manager.Close()

	scheduler := NewScheduler(manager)

	manager.RegisterWorker("worker-1", ComputeCapacity{
		CPUCores: 4,
		RAMMB:    8192,
	})

	// Get initial trust
	manager.mu.RLock()
	initialTrust := manager.workers["worker-1"].trustScore
	manager.mu.RUnlock()

	// Successful task should increase trust
	scheduler.UpdateWorkerTrust("worker-1", true)

	manager.mu.RLock()
	newTrust := manager.workers["worker-1"].trustScore
	manager.mu.RUnlock()

	if newTrust <= initialTrust {
		t.Error("Trust should increase after successful task")
	}

	// Failed task should decrease trust
	scheduler.UpdateWorkerTrust("worker-1", false)

	manager.mu.RLock()
	finalTrust := manager.workers["worker-1"].trustScore
	manager.mu.RUnlock()

	if finalTrust >= newTrust {
		t.Error("Trust should decrease after failed task")
	}
}

// MockDelegator implements TaskDelegator for testing
type MockDelegator struct {
	workers        []string
	delegateCalled atomic.Int32
}

func (m *MockDelegator) DelegateTask(ctx context.Context, workerID string, task *ComputeTask) (*TaskResult, error) {
	m.delegateCalled.Add(1)
	// Simulate successful remote execution
	return &TaskResult{
		TaskID:          task.TaskID,
		Status:          TaskCompleted,
		ResultData:      []byte("mock result"),
		ResultHash:      "mockhash",
		ExecutionTimeMs: 100,
		WorkerID:        workerID,
	}, nil
}

func (m *MockDelegator) GetAvailableWorkers() []string {
	return m.workers
}

func (m *MockDelegator) HasWorkers() bool {
	return len(m.workers) > 0
}

func TestDelegationWithDelegator(t *testing.T) {
	config := DefaultConfig()
	manager := NewManager(config)
	defer manager.Close()

	// Create a mock delegator with a worker
	mockDelegator := &MockDelegator{
		workers: []string{"remote-worker-1"},
	}
	manager.SetDelegator(mockDelegator)

	// Submit a small job - should still delegate when workers are available
	manifest := &JobManifest{
		JobID:        "test-delegation-job",
		InputData:    []byte("small data"), // Small data = low complexity
		MinChunkSize: 1,                    // Allow small chunks for testing
		MaxChunkSize: 100,
		TimeoutSecs:  60,
	}

	_, err := manager.SubmitJob(manifest)
	if err != nil {
		t.Fatalf("SubmitJob failed: %v", err)
	}

	// Wait for job processing
	time.Sleep(200 * time.Millisecond)

	// Verify that delegation was attempted even with low complexity
	// because remote workers are available
	delegateCount := mockDelegator.delegateCalled.Load()
	if delegateCount == 0 {
		t.Error("Expected DelegateTask to be called when remote workers are available")
	}
}

func TestLocalExecutionWithoutDelegator(t *testing.T) {
	config := DefaultConfig()
	manager := NewManager(config)
	defer manager.Close()

	// No delegator set - should execute locally

	manifest := &JobManifest{
		JobID:        "test-local-job",
		InputData:    []byte("small data"),
		MinChunkSize: 1,
		MaxChunkSize: 100,
		TimeoutSecs:  60,
	}

	_, err := manager.SubmitJob(manifest)
	if err != nil {
		t.Fatalf("SubmitJob failed: %v", err)
	}

	// Wait for job processing
	time.Sleep(200 * time.Millisecond)

	// Get status - should complete (locally) even without delegator
	status, err := manager.GetJobStatus("test-local-job")
	if err != nil {
		t.Fatalf("GetJobStatus failed: %v", err)
	}

	// Job should have completed or be in progress
	if status.Status == TaskPending {
		t.Error("Expected job to have started processing")
	}
}

func TestDelegatorHasWorkersCheck(t *testing.T) {
	config := DefaultConfig()
	manager := NewManager(config)
	defer manager.Close()

	// Create delegator with no workers
	emptyDelegator := &MockDelegator{
		workers: []string{}, // No workers
	}
	manager.SetDelegator(emptyDelegator)

	manifest := &JobManifest{
		JobID:        "test-empty-delegator-job",
		InputData:    []byte("data"),
		MinChunkSize: 1,
		MaxChunkSize: 100,
		TimeoutSecs:  60,
	}

	_, err := manager.SubmitJob(manifest)
	if err != nil {
		t.Fatalf("SubmitJob failed: %v", err)
	}

	// Wait for job processing
	time.Sleep(200 * time.Millisecond)

	// With no workers, DelegateTask should not be called
	delegateCount := emptyDelegator.delegateCalled.Load()
	if delegateCount != 0 {
		t.Errorf("Expected DelegateTask not to be called when no workers, but called %d times", delegateCount)
	}
}
