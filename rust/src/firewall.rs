use std::collections::HashSet;
use std::net::IpAddr;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::info;

#[cfg(feature = "ebpf")]
use tracing::warn;

/// Firewall that filters connections based on IP allowlist
pub struct Firewall {
    allowed_ips: Arc<RwLock<HashSet<IpAddr>>>,
    mode: FirewallMode,
}

#[derive(Debug, Clone, Copy)]
pub enum FirewallMode {
    /// User-space filtering (portable, works everywhere)
    UserSpace,
    /// eBPF/XDP filtering (Linux only, kernel-level)
    Ebpf,
}

impl Firewall {
    /// Create a new firewall
    pub fn new(mode: FirewallMode) -> Self {
        Self {
            allowed_ips: Arc::new(RwLock::new(HashSet::new())),
            mode,
        }
    }

    /// Add an IP to the allowlist
    pub async fn allow_ip(&self, ip: IpAddr) {
        let mut allowed = self.allowed_ips.write().await;
        allowed.insert(ip);
        info!("Added {} to firewall allowlist", ip);

        // If using eBPF, update the kernel map
        #[cfg(feature = "ebpf")]
        if matches!(self.mode, FirewallMode::Ebpf) {
            self.update_ebpf_map(ip, true).await;
        }
    }

    /// Remove an IP from the allowlist
    pub async fn block_ip(&self, ip: IpAddr) {
        let mut allowed = self.allowed_ips.write().await;
        allowed.remove(&ip);
        info!("Removed {} from firewall allowlist", ip);

        // If using eBPF, update the kernel map
        #[cfg(feature = "ebpf")]
        if matches!(self.mode, FirewallMode::Ebpf) {
            self.update_ebpf_map(ip, false).await;
        }
    }

    /// Check if an IP is allowed (user-space filtering)
    pub async fn is_allowed(&self, ip: IpAddr) -> bool {
        let allowed = self.allowed_ips.read().await;
        allowed.contains(&ip)
    }

    /// Get firewall mode
    pub fn mode(&self) -> FirewallMode {
        self.mode
    }

    /// Update eBPF map (Linux only)
    #[cfg(feature = "ebpf")]
    async fn update_ebpf_map(&self, ip: IpAddr, allow: bool) {
        // Placeholder for eBPF map update
        // In a real implementation, this would:
        // 1. Load the eBPF program if not already loaded
        // 2. Update the BPF_MAP_TYPE_HASH with the IP
        // 3. Attach to XDP if not already attached
        info!("eBPF map update: {} -> {}", ip, allow);
    }

    /// Initialize eBPF firewall (Linux only)
    #[cfg(feature = "ebpf")]
    #[allow(unused_variables)]
    pub async fn init_ebpf(&self, interface: &str) -> anyhow::Result<()> {
        #[allow(unused_imports)]
        use aya::{
            programs::{Xdp, XdpFlags},
            Bpf,
        };

        warn!("eBPF initialization not yet implemented");
        // Placeholder for eBPF initialization
        // In a real implementation:
        // 1. Load the compiled eBPF program
        // 2. Attach to the network interface using XDP
        // 3. Set up the IP allowlist map

        Ok(())
    }
}

impl Default for Firewall {
    fn default() -> Self {
        // Default to user-space filtering for portability
        Self::new(FirewallMode::UserSpace)
    }
}

/// Create an adaptive firewall based on system capabilities
pub fn create_adaptive_firewall(caps: &crate::capabilities::HardwareCaps) -> Firewall {
    let mode = if caps.has_ebpf {
        info!("eBPF support detected, using kernel-level firewall");
        FirewallMode::Ebpf
    } else {
        info!("eBPF not available, using user-space firewall");
        FirewallMode::UserSpace
    };

    Firewall::new(mode)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::str::FromStr;

    #[tokio::test]
    async fn test_firewall_allowlist() {
        let firewall = Firewall::default();
        let ip = IpAddr::from_str("127.0.0.1").unwrap();

        assert!(!firewall.is_allowed(ip).await);

        firewall.allow_ip(ip).await;
        assert!(firewall.is_allowed(ip).await);

        firewall.block_ip(ip).await;
        assert!(!firewall.is_allowed(ip).await);
    }
}
