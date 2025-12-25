use rand::RngCore;
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

/// Create a new CES pipeline instance with key from environment or random key
/// Returns an opaque handle that must be freed with ces_free()
///
/// SECURITY WARNING: For production use, prefer ces_new_with_key() to explicitly manage keys.
/// This function will:
/// 1. Check CES_ENCRYPTION_KEY environment variable (hex-encoded 64 characters)
/// 2. Fall back to a random key if not set (insecure for reconstruction across processes)
///
/// For proper key management in production, use ces_new_with_key() instead.
#[no_mangle]
#[allow(clippy::unnecessary_cast)]
pub extern "C" fn ces_new(compression_level: c_int) -> *mut CesPipeline {
    let config = CesConfig {
        compression_level: compression_level as i32,
        compression_algorithm: crate::types::CompressionAlgorithm::Zstd,
        shard_count: 8,
        parity_count: 4,
        chunk_size: 1024 * 1024, // 1MB chunks
    };

    // Try to get key from environment variable
    let encryption_key = if let Ok(key_hex) = std::env::var("CES_ENCRYPTION_KEY") {
        // Parse hex string to bytes
        if key_hex.len() == 64 {
            let mut key = [0u8; 32];
            if hex::decode_to_slice(&key_hex, &mut key).is_ok() {
                eprintln!("INFO: Using encryption key from CES_ENCRYPTION_KEY environment variable (suitable for development/testing)");
                key
            } else {
                eprintln!("WARNING: Invalid CES_ENCRYPTION_KEY format, using random key (DEVELOPMENT/TESTING ONLY - NOT for production)");
                let mut key = [0u8; 32];
                rand::thread_rng().fill_bytes(&mut key);
                key
            }
        } else {
            eprintln!("WARNING: CES_ENCRYPTION_KEY must be 64 hex characters (32 bytes), using random key (DEVELOPMENT/TESTING ONLY - NOT for production)");
            let mut key = [0u8; 32];
            rand::thread_rng().fill_bytes(&mut key);
            key
        }
    } else {
        // No environment variable set, use random key
        eprintln!("WARNING: No CES_ENCRYPTION_KEY set, using random key. EPHEMERAL TESTING ONLY - data cannot be reconstructed across process restarts. Use ces_new_with_key() for production.");
        let mut key = [0u8; 32];
        rand::thread_rng().fill_bytes(&mut key);
        key
    };

    let pipeline = CesPipeline::new(config).with_key(encryption_key);
    Box::into_raw(Box::new(pipeline))
}

/// Create a new CES pipeline instance with an explicit encryption key
/// Returns an opaque handle that must be freed with ces_free()
///
/// This is the recommended function for production use as it allows explicit key management.
/// The key must be 32 bytes (256 bits) for XChaCha20-Poly1305 encryption.
///
/// # Safety
/// The caller must ensure the key pointer is valid and points to exactly 32 bytes.
/// This function dereferences raw pointers and must only be called with valid pointers
#[no_mangle]
#[allow(clippy::not_unsafe_ptr_arg_deref)]
#[allow(clippy::unnecessary_cast)]
pub extern "C" fn ces_new_with_key(
    compression_level: c_int,
    key: *const c_uchar,
) -> *mut CesPipeline {
    if key.is_null() {
        eprintln!("ERROR: Null key pointer provided to ces_new_with_key");
        return std::ptr::null_mut();
    }

    let config = CesConfig {
        compression_level: compression_level as i32,
        compression_algorithm: crate::types::CompressionAlgorithm::Zstd,
        shard_count: 8,
        parity_count: 4,
        chunk_size: 1024 * 1024, // 1MB chunks
    };

    // Copy the key from the provided pointer
    let mut encryption_key = [0u8; 32];
    unsafe {
        std::ptr::copy_nonoverlapping(key, encryption_key.as_mut_ptr(), 32);
    }

    let pipeline = CesPipeline::new(config).with_key(encryption_key);
    Box::into_raw(Box::new(pipeline))
}

/// Free a CES pipeline instance
/// 
/// # Safety
/// This function dereferences raw pointers and must only be called with valid pointers
#[no_mangle]
#[allow(clippy::not_unsafe_ptr_arg_deref)]
pub extern "C" fn ces_free(pipeline: *mut CesPipeline) {
    if !pipeline.is_null() {
        unsafe {
            drop(Box::from_raw(pipeline));
        }
    }
}

/// Process data through CES pipeline (Compress, Encrypt, Shard)
/// Returns FFIShards structure that must be freed with ces_free_shards()
/// 
/// # Safety
/// This function dereferences raw pointers and must only be called with valid pointers
#[no_mangle]
#[allow(clippy::not_unsafe_ptr_arg_deref)]
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
/// 
/// # Safety
/// This function dereferences raw pointers and must only be called with valid pointers
#[no_mangle]
#[allow(clippy::not_unsafe_ptr_arg_deref)]
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
            let _ = Box::from_raw(std::ptr::slice_from_raw_parts_mut(result.data, result.data_len));
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
                let _ = Box::from_raw(std::ptr::slice_from_raw_parts_mut(shard.data, shard.len));
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
        let result = ces_reconstruct(pipeline, shards.shards, shards.count, present.as_ptr());

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

    #[test]
    fn test_ffi_with_explicit_key() {
        // Create a deterministic key for testing
        let key = [0x42u8; 32];

        // Create first pipeline with explicit key
        let pipeline1 = ces_new_with_key(3, key.as_ptr());
        assert!(!pipeline1.is_null());

        // Test data
        let test_data = b"Testing explicit key management for CES pipeline security.";

        // Process with first pipeline
        let shards = ces_process(pipeline1, test_data.as_ptr(), test_data.len());
        assert!(shards.count > 0);
        assert!(!shards.shards.is_null());

        // Copy shards for reconstruction test
        let shard_count = shards.count;
        let mut shard_copies = Vec::with_capacity(shard_count);
        unsafe {
            let shards_slice = slice::from_raw_parts(shards.shards, shard_count);
            for shard in shards_slice {
                let shard_data = slice::from_raw_parts(shard.data, shard.len).to_vec();
                shard_copies.push(shard_data);
            }
        }

        // Clean up first pipeline
        ces_free_shards(shards);
        ces_free(pipeline1);

        // Create second pipeline with SAME key
        let pipeline2 = ces_new_with_key(3, key.as_ptr());
        assert!(!pipeline2.is_null());

        // Reconstruct using second pipeline
        let mut ffi_shards = Vec::with_capacity(shard_count);
        for shard_data in &shard_copies {
            let data = Box::into_raw(shard_data.clone().into_boxed_slice()) as *mut c_uchar;
            ffi_shards.push(FFIShard {
                data,
                len: shard_data.len(),
            });
        }

        let present = vec![1i32; shard_count];
        let result = ces_reconstruct(
            pipeline2,
            ffi_shards.as_ptr(),
            shard_count,
            present.as_ptr(),
        );

        assert!(result.success);
        assert!(!result.data.is_null());

        // Verify data matches original
        unsafe {
            let reconstructed = slice::from_raw_parts(result.data, result.data_len);
            assert_eq!(reconstructed, test_data);
        }

        // Cleanup
        ces_free_result(result);
        for shard in ffi_shards {
            unsafe {
                if !shard.data.is_null() {
                    let _ = Box::from_raw(std::ptr::slice_from_raw_parts_mut(shard.data, shard.len));
                }
            }
        }
        ces_free(pipeline2);
    }
}
