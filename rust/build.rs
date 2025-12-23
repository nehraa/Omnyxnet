// Build script to compile Cap'n Proto schemas
use std::path::PathBuf;
use std::process::Command;

fn main() {
    // Check if capnp is installed
    let capnp_available = Command::new("capnp").arg("--version").output().is_ok();

    if !capnp_available {
        println!("cargo:warning=Cap'n Proto compiler (capnp) not found.");
        println!("cargo:warning=RPC functionality will be limited. Install capnp to enable full RPC support.");
        println!("cargo:warning=  macOS: brew install capnp");
        println!("cargo:warning=  Ubuntu/Debian: apt-get install capnproto");
        return;
    }

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

    println!("cargo:rerun-if-changed=schema.capnp");
}
