// Build script to compile Cap'n Proto schemas
use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn main() {
    let out_dir = std::env::var("OUT_DIR").expect("OUT_DIR not set by Cargo");
    let generated_schema = PathBuf::from(&out_dir).join("schema_capnp.rs");
    let pre_generated = PathBuf::from("src/schema_capnp.rs");

    // Skip live schema generation to avoid version skew; use pre-generated bindings instead.
    println!("cargo:warning=Using pre-generated Cap'n Proto bindings (schema_capnp.rs)");

    // Ensure generated schema exists using the pre-generated file
    if pre_generated.exists() {
        if let Err(err) = fs::copy(&pre_generated, &generated_schema) {
            panic!("Failed to copy pre-generated Cap'n Proto bindings: {}", err);
        }
    }

    println!("cargo:rerun-if-changed=schema.capnp");
    println!("cargo:rerun-if-changed=src/schema_capnp.rs");
}
