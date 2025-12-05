package main

/*
#cgo LDFLAGS: -L../rust/target/release -lpangea_ces -ldl -lm
#cgo CFLAGS: -I.
#include <stdlib.h>
#include <stdint.h>

// FFI Result structure (matches Rust)
typedef struct {
    uint8_t success;
    char* error_msg;
    uint8_t* data;
    size_t data_len;
} FFIResult;

// FFI Shard structure (matches Rust)
typedef struct {
    uint8_t* data;
    size_t len;
} FFIShard;

// FFI Shards array structure (matches Rust)
typedef struct {
    FFIShard* shards;
    size_t count;
} FFIShards;

// Forward declarations for Rust FFI functions
void* ces_new(int compression_level);
void* ces_new_with_key(int compression_level, const uint8_t* key);
void ces_free(void* pipeline);
FFIShards ces_process(void* pipeline, const uint8_t* data, size_t data_len);
FFIResult ces_reconstruct(void* pipeline, const FFIShard* shards, size_t shard_count, const int* shard_present);
void ces_free_result(FFIResult result);
void ces_free_shards(FFIShards shards);
*/
import "C"
import (
	"fmt"
	"unsafe"
)

// CESPipeline represents a Rust CES pipeline instance
type CESPipeline struct {
	handle unsafe.Pointer
}

// ShardData represents raw shard data (avoid conflict with generated Shard type)
type ShardData struct {
	Data []byte
}

// NewCESPipeline creates a new CES pipeline with the specified compression level
// Uses environment variable CES_ENCRYPTION_KEY or generates a random key
// For production, use NewCESPipelineWithKey for explicit key management
func NewCESPipeline(compressionLevel int) *CESPipeline {
	handle := C.ces_new(C.int(compressionLevel))
	if handle == nil {
		return nil
	}
	return &CESPipeline{handle: handle}
}

// NewCESPipelineWithKey creates a new CES pipeline with an explicit encryption key
// The key must be exactly 32 bytes (256 bits) for XChaCha20-Poly1305 encryption
// This is the recommended function for production use
func NewCESPipelineWithKey(compressionLevel int, key [32]byte) *CESPipeline {
	handle := C.ces_new_with_key(C.int(compressionLevel), (*C.uint8_t)(&key[0]))
	if handle == nil {
		return nil
	}
	return &CESPipeline{handle: handle}
}

// Close frees the CES pipeline resources
func (c *CESPipeline) Close() {
	if c.handle != nil {
		C.ces_free(c.handle)
		c.handle = nil
	}
}

// Process data through the CES pipeline (Compress, Encrypt, Shard)
func (c *CESPipeline) Process(data []byte) ([]ShardData, error) {
	if c.handle == nil {
		return nil, fmt.Errorf("pipeline is closed")
	}
	if len(data) == 0 {
		return nil, fmt.Errorf("data is empty")
	}

	// Call Rust FFI
	ffiShards := C.ces_process(
		c.handle,
		(*C.uint8_t)(unsafe.Pointer(&data[0])),
		C.size_t(len(data)),
	)
	defer C.ces_free_shards(ffiShards)

	// Check for error
	if ffiShards.shards == nil || ffiShards.count == 0 {
		return nil, fmt.Errorf("CES processing failed")
	}

	// Validate shard count to prevent out-of-bounds access
	// Use a reasonable limit based on expected use cases (100 shards * 1MB = 100MB)
	const maxShardCount = 1000
	if ffiShards.count > maxShardCount {
		return nil, fmt.Errorf("shard count too large: %d (max %d)", ffiShards.count, maxShardCount)
	}

	// Validate the total size doesn't exceed reasonable limits
	// This helps catch corrupted FFI responses
	const maxTotalSize = 1 << 30 // 1GB total max
	totalSize := uint64(0)

	// Pre-validate all shards before processing
	// Use maxShardCount for the backing array to match the validation above
	shardCount := int(ffiShards.count)
	cShards := (*[maxShardCount]C.FFIShard)(unsafe.Pointer(ffiShards.shards))[:shardCount:shardCount]

	for i := 0; i < shardCount; i++ {
		if cShards[i].data == nil {
			return nil, fmt.Errorf("shard %d has no data", i)
		}
		shardLen := uint64(cShards[i].len)
		if shardLen > maxTotalSize {
			return nil, fmt.Errorf("shard %d size too large: %d", i, shardLen)
		}
		totalSize += shardLen
		if totalSize > maxTotalSize {
			return nil, fmt.Errorf("total shard size exceeds limit: %d > %d", totalSize, maxTotalSize)
		}
	}

	// Convert C shards to Go
	shards := make([]ShardData, shardCount)
	for i := 0; i < shardCount; i++ {
		// Copy shard data to Go
		shardData := C.GoBytes(unsafe.Pointer(cShards[i].data), C.int(cShards[i].len))
		shards[i] = ShardData{Data: shardData}
	}

	return shards, nil
}

// Reconstruct data from shards (reverse CES pipeline)
func (c *CESPipeline) Reconstruct(shards []ShardData, present []bool) ([]byte, error) {
	if c.handle == nil {
		return nil, fmt.Errorf("pipeline is closed")
	}
	if len(shards) == 0 {
		return nil, fmt.Errorf("no shards provided")
	}
	if len(shards) != len(present) {
		return nil, fmt.Errorf("shards and present arrays must have same length")
	}

	// Convert Go shards to C
	cShards := make([]C.FFIShard, len(shards))
	cPresent := make([]C.int, len(present))

	for i := 0; i < len(shards); i++ {
		if present[i] && len(shards[i].Data) > 0 {
			cShards[i].data = (*C.uint8_t)(C.CBytes(shards[i].Data))
			cShards[i].len = C.size_t(len(shards[i].Data))
			cPresent[i] = 1
		} else {
			cShards[i].data = nil
			cShards[i].len = 0
			cPresent[i] = 0
		}
	}

	// Cleanup C memory
	defer func() {
		for i := 0; i < len(shards); i++ {
			if cShards[i].data != nil {
				C.free(unsafe.Pointer(cShards[i].data))
			}
		}
	}()

	// Call Rust FFI
	result := C.ces_reconstruct(
		c.handle,
		(*C.FFIShard)(unsafe.Pointer(&cShards[0])),
		C.size_t(len(shards)),
		(*C.int)(unsafe.Pointer(&cPresent[0])),
	)
	defer C.ces_free_result(result)

	// Check for error
	if result.success == 0 {
		errMsg := ""
		if result.error_msg != nil {
			errMsg = C.GoString(result.error_msg)
		}
		return nil, fmt.Errorf("CES reconstruction failed: %s", errMsg)
	}

	// Convert result to Go
	if result.data == nil || result.data_len == 0 {
		return nil, fmt.Errorf("reconstruction returned no data")
	}

	reconstructed := C.GoBytes(unsafe.Pointer(result.data), C.int(result.data_len))
	return reconstructed, nil
}

// Example usage:
// pipeline := NewCESPipeline(3)
// defer pipeline.Close()
// shards, err := pipeline.Process(data)
// reconstructed, err := pipeline.Reconstruct(shards, present)
