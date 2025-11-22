use sysinfo::{System, SystemExt};

pub struct HardwareCaps {
    pub has_avx2: bool,
    pub has_neon: bool,
    pub has_io_uring: bool,
    pub has_ebpf: bool,
    pub ram_gb: u64,
    pub cpu_cores: usize,
}

impl HardwareCaps {
    pub fn probe() -> Self {
        let mut sys = System::new_all();
        sys.refresh_all();

        let kernel_supports_uring = check_kernel_version_supports_io_uring();

        let avx2 = if cfg!(target_arch = "x86_64") {
            // runtime detection would use is_x86_feature_detected!, keep conservative false for portability
            false
        } else {
            false
        };

        let neon = if cfg!(target_arch = "aarch64") { false } else { false };

        Self {
            has_avx2: avx2,
            has_neon: neon,
            has_io_uring: kernel_supports_uring && cfg!(target_os = "linux"),
            has_ebpf: cfg!(target_os = "linux") && check_has_root(),
            ram_gb: sys.total_memory() / 1024 / 1024 / 1024,
            cpu_cores: sys.cpus().len(),
        }
    }
}

fn check_kernel_version_supports_io_uring() -> bool {
    // For scaffold, only return true on linux AND if /proc/version contains a recent kernel number
    #[cfg(target_os = "linux")]
    {
        // Very small heuristic: attempt to read /proc/version
        if let Ok(v) = std::fs::read_to_string("/proc/version") {
            if v.contains("5.") || v.contains("6.") {
                return true;
            }
        }
        false
    }
    #[cfg(not(target_os = "linux"))]
    {
        false
    }
}

fn check_has_root() -> bool {
    #[cfg(target_family = "unix")]
    {
        unsafe { libc::geteuid() == 0 }
    }
    #[cfg(not(target_family = "unix"))]
    {
        false
    }
}
