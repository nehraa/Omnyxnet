package main

import (
	"encoding/binary"
	"fmt"
	"os"
	"sync"
	"syscall"
	"unsafe"
)

// SharedMemoryRing implements a lock-free ring buffer in shared memory
// for high-performance data streaming between Go and Python
type SharedMemoryRing struct {
	name     string
	size     int
	fd       int
	data     []byte
	mu       sync.RWMutex
	writePos uint64
	readPos  uint64
}

const (
	// Ring buffer layout in shared memory:
	// [0-7]: write position (8 bytes)
	// [8-15]: read position (8 bytes)
	// [16-23]: total messages written (8 bytes)
	// [24-31]: total messages read (8 bytes)
	// [32...]: ring buffer data
	HeaderSize     = 32
	MaxMessageSize = 64 * 1024 * 1024 // 64MB max message size
)

// NewSharedMemoryRing creates or opens a shared memory ring buffer
func NewSharedMemoryRing(name string, size int) (*SharedMemoryRing, error) {
	shmPath := fmt.Sprintf("/dev/shm/pangea_%s", name)

	// Create or open shared memory file
	fd, err := syscall.Open(shmPath, syscall.O_RDWR|syscall.O_CREAT, 0666)
	if err != nil {
		return nil, fmt.Errorf("failed to open shared memory: %w", err)
	}

	totalSize := HeaderSize + size

	// Set file size
	if err := syscall.Ftruncate(fd, int64(totalSize)); err != nil {
		syscall.Close(fd)
		return nil, fmt.Errorf("failed to set size: %w", err)
	}

	// Memory map the file
	data, err := syscall.Mmap(fd, 0, totalSize, syscall.PROT_READ|syscall.PROT_WRITE, syscall.MAP_SHARED)
	if err != nil {
		syscall.Close(fd)
		return nil, fmt.Errorf("failed to mmap: %w", err)
	}

	ring := &SharedMemoryRing{
		name: name,
		size: size,
		fd:   fd,
		data: data,
	}

	// Initialize header if this is a new buffer
	ring.writePos = ring.getWritePos()
	ring.readPos = ring.getReadPos()

	return ring, nil
}

// getWritePos reads the write position from shared memory
func (r *SharedMemoryRing) getWritePos() uint64 {
	return binary.LittleEndian.Uint64(r.data[0:8])
}

// setWritePos updates the write position in shared memory
func (r *SharedMemoryRing) setWritePos(pos uint64) {
	binary.LittleEndian.PutUint64(r.data[0:8], pos)
}

// getReadPos reads the read position from shared memory
func (r *SharedMemoryRing) getReadPos() uint64 {
	return binary.LittleEndian.Uint64(r.data[8:16])
}

// setReadPos updates the read position in shared memory
func (r *SharedMemoryRing) setReadPos(pos uint64) {
	binary.LittleEndian.PutUint64(r.data[8:16], pos)
}

// Write writes a message to the ring buffer
// Returns the offset in shared memory where the data was written
func (r *SharedMemoryRing) Write(data []byte) (uint64, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	if len(data) > MaxMessageSize {
		return 0, fmt.Errorf("message too large: %d bytes (max %d)", len(data), MaxMessageSize)
	}

	// Message format: [4 bytes length][data]
	msgSize := 4 + len(data)

	writePos := r.getWritePos()
	readPos := r.getReadPos()

	// Check if there's enough space
	available := r.size
	if writePos >= readPos {
		available = r.size - int(writePos-readPos)
	} else {
		available = int(readPos - writePos)
	}

	if msgSize > available {
		return 0, fmt.Errorf("ring buffer full: need %d bytes, have %d", msgSize, available)
	}

	// Calculate actual position in ring buffer
	offset := HeaderSize + (writePos % uint64(r.size))

	// Write length prefix
	binary.LittleEndian.PutUint32(r.data[offset:offset+4], uint32(len(data)))

	// Write data (may wrap around)
	dataOffset := offset + 4
	remaining := uint64(r.size) - (dataOffset - HeaderSize)

	if uint64(len(data)) <= remaining {
		// Fits without wrapping
		copy(r.data[dataOffset:dataOffset+uint64(len(data))], data)
	} else {
		// Wrap around
		copy(r.data[dataOffset:HeaderSize+uint64(r.size)], data[:remaining])
		copy(r.data[HeaderSize:], data[remaining:])
	}

	// Update write position
	newWritePos := writePos + uint64(msgSize)
	r.setWritePos(newWritePos)
	r.writePos = newWritePos

	// Return the offset for RPC pointer passing
	return offset, nil
}

// Read reads a message from the ring buffer
func (r *SharedMemoryRing) Read() ([]byte, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	writePos := r.getWritePos()
	readPos := r.getReadPos()

	// Check if buffer is empty
	if readPos >= writePos {
		return nil, fmt.Errorf("ring buffer empty")
	}

	// Calculate actual position in ring buffer
	offset := HeaderSize + (readPos % uint64(r.size))

	// Read length prefix
	msgLen := binary.LittleEndian.Uint32(r.data[offset : offset+4])
	if msgLen > MaxMessageSize {
		return nil, fmt.Errorf("corrupted message: length %d exceeds max", msgLen)
	}

	// Read data
	dataOffset := offset + 4
	data := make([]byte, msgLen)
	remaining := uint64(r.size) - (dataOffset - HeaderSize)

	if uint64(msgLen) <= remaining {
		// No wrap around
		copy(data, r.data[dataOffset:dataOffset+uint64(msgLen)])
	} else {
		// Wrap around
		copy(data[:remaining], r.data[dataOffset:HeaderSize+uint64(r.size)])
		copy(data[remaining:], r.data[HeaderSize:])
	}

	// Update read position
	newReadPos := readPos + 4 + uint64(msgLen)
	r.setReadPos(newReadPos)
	r.readPos = newReadPos

	return data, nil
}

// ReadAt reads a message at a specific offset (for RPC pointer passing)
func (r *SharedMemoryRing) ReadAt(offset uint64) ([]byte, error) {
	if offset < HeaderSize || offset >= uint64(len(r.data)) {
		return nil, fmt.Errorf("invalid offset: %d", offset)
	}

	// Read length prefix
	msgLen := binary.LittleEndian.Uint32(r.data[offset : offset+4])
	if msgLen > MaxMessageSize {
		return nil, fmt.Errorf("corrupted message: length %d exceeds max", msgLen)
	}

	// Read data
	dataOffset := offset + 4
	data := make([]byte, msgLen)
	remaining := uint64(r.size) - (dataOffset - HeaderSize)

	if uint64(msgLen) <= remaining {
		copy(data, r.data[dataOffset:dataOffset+uint64(msgLen)])
	} else {
		copy(data[:remaining], r.data[dataOffset:HeaderSize+uint64(r.size)])
		copy(data[remaining:], r.data[HeaderSize:])
	}

	return data, nil
}

// GetStats returns buffer statistics
func (r *SharedMemoryRing) GetStats() (writePos, readPos uint64, used int) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	writePos = r.getWritePos()
	readPos = r.getReadPos()
	used = int(writePos - readPos)

	return
}

// Close unmaps and closes the shared memory
func (r *SharedMemoryRing) Close() error {
	if err := syscall.Munmap(r.data); err != nil {
		return err
	}
	if err := syscall.Close(r.fd); err != nil {
		return err
	}

	// Optionally remove the shared memory file
	shmPath := fmt.Sprintf("/dev/shm/pangea_%s", r.name)
	os.Remove(shmPath)

	return nil
}

// Cleanup removes a shared memory segment
func CleanupSharedMemory(name string) error {
	shmPath := fmt.Sprintf("/dev/shm/pangea_%s", name)
	return os.Remove(shmPath)
}

// SharedMemoryManager manages multiple shared memory rings
type SharedMemoryManager struct {
	rings map[string]*SharedMemoryRing
	mu    sync.RWMutex
}

func NewSharedMemoryManager() *SharedMemoryManager {
	return &SharedMemoryManager{
		rings: make(map[string]*SharedMemoryRing),
	}
}

func (m *SharedMemoryManager) CreateRing(name string, size int) (*SharedMemoryRing, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, exists := m.rings[name]; exists {
		return nil, fmt.Errorf("ring %s already exists", name)
	}

	ring, err := NewSharedMemoryRing(name, size)
	if err != nil {
		return nil, err
	}

	m.rings[name] = ring
	return ring, nil
}

func (m *SharedMemoryManager) GetRing(name string) (*SharedMemoryRing, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	ring, ok := m.rings[name]
	return ring, ok
}

func (m *SharedMemoryManager) CloseAll() error {
	m.mu.Lock()
	defer m.mu.Unlock()

	for _, ring := range m.rings {
		if err := ring.Close(); err != nil {
			return err
		}
	}
	m.rings = make(map[string]*SharedMemoryRing)
	return nil
}

// Helper function to get pointer to shared memory data
func (r *SharedMemoryRing) GetDataPointer() uintptr {
	return uintptr(unsafe.Pointer(&r.data[0]))
}
