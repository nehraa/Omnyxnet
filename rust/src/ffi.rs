/// FFI layer for Go ↔ Rust interop
/// Exposes CES pipeline functions as C-compatible API
use std::ffi::CString;
use std::os::raw::{c_char, c_int, c_uchar};
use std::slice;

use crate::ces::CesPipeline;
use crate::types::CesConfig;

/// FFI Result structure
#[repr(C)]
pub struct FFIResult {
    pub success: bool,
    pub error_msg: *mut c_char,
    pub data: *mut c_uchar,
    pub data_len: usize,
}

/// FFI Shard structure
#[repr(C)]
pub struct FFIShard {
    pub data: *mut c_uchar,
    pub len: usize,
}

/// FFI Shards array structure
#[repr(C)]
pub struct FFIShards {
    pub shards: *mut FFIShard,
    pub count: usize,
}

/// Create a new CES pipeline instance
/// Returns an opaque handle that must be freed with ces_free()
#[no_mangle]
pub extern "C" fn ces_new(compression_level: c_int) -> *mut CesPipeline {
    let config = CesConfig {
        compression_level: compression_level as i32,
        shard_count: 8,
        parity_count: 4,
        chunk_size: 1024 * 1024, // 1MB chunks
    };
    
    // SECURITY WARNING: This implementation uses a fixed encryption key for testing only.
    // All CES pipeline instances created by ces_new() will use the same key, which is insecure for production
    // and prevents secure multi-user or multi-tenant scenarios.
    //
    // In production, key management should be implemented via one of the following approaches:
    //   1. Passing keys as parameters to ces_new(), or
    //   2. Using a separate ces_set_key() function, or
    //   3. Deriving keys from a shared secret management system.
    //
    // Failing to do so may result in compromise of all data protected by this pipeline.
    let deterministic_key = [0x42u8; 32]; // Fixed key for testing
    let pipeline = CesPipeline::new(config).with_key(deterministic_key);
    Box::into_raw(Box::new(pipeline))
}

/// Free a CES pipeline instance
#[no_mangle]
pub extern "C" fn ces_free(pipeline: *mut CesPipeline) {
    if !pipeline.is_null() {
        unsafe {
            drop(Box::from_raw(pipeline));
        }
    }
}

/// Process data through CES pipeline (Compress, Encrypt, Shard)
/// Returns FFIShards structure that must be freed with ces_free_shards()
#[no_mangle]
pub extern "C" fn ces_process(
    pipeline: *const CesPipeline,
    data: *const c_uchar,
    data_len: usize,
) -> FFIShards {
    // Safety checks
    if pipeline.is_null() || data.is_null() {
        return FFIShards {
            shards: std::ptr::null_mut(),
            count: 0,
        };
    }

    unsafe {
        let pipeline = &*pipeline;
        let input = slice::from_raw_parts(data, data_len);

        // Process through CES pipeline
        match pipeline.process(input) {
            Ok(shards) => {
                let count = shards.len();
                let mut ffi_shards = Vec::with_capacity(count);

                for shard in shards {
                    let len = shard.len();
                    let data = Box::into_raw(shard.into_boxed_slice()) as *mut c_uchar;
                    ffi_shards.push(FFIShard { data, len });
                }

                let shards_ptr = Box::into_raw(ffi_shards.into_boxed_slice()) as *mut FFIShard;
                FFIShards {
                    shards: shards_ptr,
                    count,
                }
            }
            Err(_) => FFIShards {
                shards: std::ptr::null_mut(),
                count: 0,
            },
        }
    }
}

/// Reconstruct data from shards (reverse CES pipeline)
/// shard_present array indicates which shards are available (1) or missing (0)
#[no_mangle]
pub extern "C" fn ces_reconstruct(
    pipeline: *const CesPipeline,
    shards: *const FFIShard,
    shard_count: usize,
    shard_present: *const c_int,
) -> FFIResult {
    // Safety checks
    if pipeline.is_null() || shards.is_null() || shard_present.is_null() {
        return FFIResult {
            success: false,
            error_msg: create_error_string("Invalid parameters"),
            data: std::ptr::null_mut(),
            data_len: 0,
        };
    }

    unsafe {
        let pipeline = &*pipeline;
        let shards_slice = slice::from_raw_parts(shards, shard_count);
        let present_slice = slice::from_raw_parts(shard_present, shard_count);

        // Convert FFIShards to Vec<Option<Vec<u8>>>
        let mut rust_shards = Vec::with_capacity(shard_count);
        for (i, ffi_shard) in shards_slice.iter().enumerate() {
            if present_slice[i] != 0 {
                let data = slice::from_raw_parts(ffi_shard.data, ffi_shard.len).to_vec();
                rust_shards.push(Some(data));
            } else {
                rust_shards.push(None);
            }
        }

        // Reconstruct
        match pipeline.reconstruct(rust_shards) {
            Ok(data) => {
                let len = data.len();
                let data_ptr = Box::into_raw(data.into_boxed_slice()) as *mut c_uchar;
                FFIResult {
                    success: true,
                    error_msg: std::ptr::null_mut(),
                    data: data_ptr,
                    data_len: len,
                }
            }
            Err(e) => FFIResult {
                success: false,
                error_msg: create_error_string(&e.to_string()),
                data: std::ptr::null_mut(),
                data_len: 0,
            },
        }
    }
}

/// Free FFI result data
#[no_mangle]
pub extern "C" fn ces_free_result(result: FFIResult) {
    unsafe {
        if !result.data.is_null() {
            // Reconstruct the boxed slice that was created with Box::into_raw
            let _ = Box::from_raw(slice::from_raw_parts_mut(result.data, result.data_len));
        }
        if !result.error_msg.is_null() {
            drop(CString::from_raw(result.error_msg));
        }
    }
}

/// Free FFI shards structure
#[no_mangle]
pub extern "C" fn ces_free_shards(shards: FFIShards) {
    if shards.shards.is_null() {
        return;
    }

    unsafe {
        let shards_vec = Vec::from_raw_parts(shards.shards, shards.count, shards.count);
        for shard in shards_vec {
            if !shard.data.is_null() {
                // Reconstruct the boxed slice that was created with Box::into_raw
                let _ = Box::from_raw(slice::from_raw_parts_mut(shard.data, shard.len));
            }
        }
    }
}

/// Helper to create error strings for FFI
fn create_error_string(msg: &str) -> *mut c_char {
    match CString::new(msg) {
        Ok(s) => s.into_raw(),
        Err(e) => {
            eprintln!("FFI Error: Failed to create error string: {}", e);
            // Return a generic error string
            CString::new("FFI error occurred").unwrap().into_raw()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ffi_roundtrip() {
        // Create pipeline
        let pipeline = ces_new(3);
        assert!(!pipeline.is_null());

        // Test data
        let test_data = b"Hello, FFI World! This is a test of the CES pipeline through FFI.";
        
        // Process
        let shards = ces_process(pipeline, test_data.as_ptr(), test_data.len());
        assert!(shards.count > 0);
        assert!(!shards.shards.is_null());

        // Mark all shards as present
        let present = vec![1i32; shards.count];
        
        // Reconstruct
        let result = ces_reconstruct(
            pipeline,
            shards.shards,
            shards.count,
            present.as_ptr(),
        );
        
        assert!(result.success);
        assert!(!result.data.is_null());
        
        // Verify data
        unsafe {
            let reconstructed = slice::from_raw_parts(result.data, result.data_len);
            assert_eq!(reconstructed, test_data);
        }

        // Cleanup
        ces_free_result(result);
        ces_free_shards(shards);
        ces_free(pipeline);
    }
}
