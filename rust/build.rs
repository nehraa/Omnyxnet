// Build script to compile Cap'n Proto schemas
use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn main() {
    let out_dir = std::env::var("OUT_DIR").expect("OUT_DIR not set by Cargo");
    let generated_schema = PathBuf::from(&out_dir).join("schema_capnp.rs");
    let pre_generated = PathBuf::from("src/schema_capnp.rs");

    // Check if capnp is installed
    let capnp_available = Command::new("capnp").arg("--version").output().is_ok();

    if capnp_available {
        // Compile the schema from rust/schema.capnp (Rust-compatible version)
        // Can be overridden with CAPNP_SCHEMA_PATH environment variable
        let schema_path = std::env::var("CAPNP_SCHEMA_PATH")
            .map(PathBuf::from)
            .unwrap_or_else(|_| PathBuf::from("schema.capnp"));

        if schema_path.exists() {
            match capnpc::CompilerCommand::new().file(&schema_path).run() {
                Ok(_) => println!("cargo:warning=Cap'n Proto schema compiled successfully"),
                Err(e) => {
                    println!("cargo:warning=Failed to compile Cap'n Proto schema: {}", e);
                    println!("cargo:warning=RPC functionality will be limited");
                }
            }
        } else {
            println!(
                "cargo:warning=Schema file not found at {:?}, skipping Cap'n Proto compilation",
                schema_path
            );
        }
    } else {
        println!("cargo:warning=Cap'n Proto compiler (capnp) not found.");
        println!("cargo:warning=RPC functionality will be limited. Install capnp to enable full RPC support.");
        println!("cargo:warning=  macOS: brew install capnp");
        println!("cargo:warning=  Ubuntu/Debian: apt-get install capnproto");
    }

    // Fallback: ensure generated schema exists even when capnp compiler is missing
    if !generated_schema.exists() && pre_generated.exists() {
        if let Err(err) = fs::copy(&pre_generated, &generated_schema) {
            panic!("Failed to copy pre-generated Cap'n Proto bindings: {}", err);
        }
    }

    println!("cargo:rerun-if-changed=schema.capnp");
    println!("cargo:rerun-if-changed=src/schema_capnp.rs");
}
