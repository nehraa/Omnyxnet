# mDNS Auto-Discovery

**Version:** 0.3.0-alpha  
**Last Updated:** 2025-11-22  
**Status:** ✅ Implemented and Working

## What is mDNS?

**mDNS (Multicast DNS)** is a protocol that allows devices on the same local network to discover each other without any central server or manual configuration. It's the technology behind features like "Network Neighborhood" and Apple's Bonjour.

## How Pangea Net Uses mDNS

Pangea Net uses mDNS for **automatic peer discovery** on local networks:

1. **Zero Configuration**: Start nodes without specifying bootstrap peers
2. **Automatic Discovery**: Nodes broadcast their presence and listen for others
3. **Instant Connection**: When peers are discovered, they automatically connect
4. **Local Network Only**: Works on the same subnet (WiFi/Ethernet)

## Implementation Details

### Code Location
- **File**: `go/libp2p_node.go`
- **Service**: libp2p's built-in mDNS service
- **Topic**: `pangea-network`

### How It Works

```go
// 1. Create mDNS notifee (handles discovery events)
notifee := &discoveryNotifee{testMode: testMode}

// 2. Initialize mDNS service
mdnsService := mdns.NewMdnsService(host, PangeaDiscoveryTopic, notifee)

// 3. When a peer is discovered, automatically connect
func (n *discoveryNotifee) HandlePeerFound(pi peer.AddrInfo) {
    log.Printf("📡 mDNS discovered local peer: %s", shortPeerID(pi.ID))
    
    // Check if already connected
    if n.node.host.Network().Connectedness(pi.ID) == network.Connected {
        return
    }
    
    // Auto-connect in background
    go func() {
        if _, err := n.node.connectPeerInfo(pi); err != nil {
            log.Printf("❌ Failed to auto-connect: %v", err)
        } else {
            log.Printf("✅ Successfully connected to mDNS peer")
        }
    }()
}
```

### Discovery Flow

```
Node 1 Starts                    Node 2 Starts
     |                                |
     v                                v
Broadcast presence              Broadcast presence
on local network                on local network
     |                                |
     +--------→ mDNS ←-----------------+
                 |
                 v
        Both nodes discover
        each other's multiaddr
                 |
                 v
        Automatic connection
        established via libp2p
```

## Testing mDNS

### Quick Test

```bash
# Automated test with 3 local nodes
./scripts/test_mdns.sh
```

This script:
1. Starts 3 nodes **without** bootstrap peers
2. Waits for mDNS discovery (1-5 seconds)
3. Verifies automatic connections
4. Shows detailed logs

### Manual Test

**Terminal 1:**
```bash
./scripts/easy_test.sh
# Select option 1 (first device)
```

**Terminal 2:**
```bash
./scripts/easy_test.sh
# Select option 1 again (no bootstrap needed!)
```

Watch the logs - they should discover and connect automatically!

### Expected Log Output

**Node 1:**
```
📡 mDNS service initialized - local peers will auto-connect
📍 Node ID: 12D3KooWXXX...
📡 mDNS discovered local peer: 12D3KooW...
🔗 Auto-connecting to mDNS peer 12D3KooW...
✅ Successfully connected to mDNS peer 12D3KooW
```

**Node 2:**
```
📡 mDNS service initialized - local peers will auto-connect
📍 Node ID: 12D3KooWYYY...
📡 mDNS discovered local peer: 12D3KooW...
🔗 Auto-connecting to mDNS peer 12D3KooW...
✅ Successfully connected to mDNS peer 12D3KooW
```

## When to Use mDNS vs Manual Connection

### Use mDNS When:
- ✅ Testing on the same local network (WiFi/Ethernet)
- ✅ Developing locally with multiple nodes
- ✅ Quick demos without configuration
- ✅ Home/office network deployments

### Use Manual Connection When:
- 🌐 Nodes are on different networks (WAN)
- 🌐 Connecting across the internet
- 🌐 Production deployments with known peers
- 🌐 Firewall/security requirements

## Limitations

1. **Same Subnet Only**: mDNS only works on the same local network segment
2. **Not Suitable for WAN**: Cannot discover peers across the internet
3. **No Security**: Discovery is unauthenticated (connections are still secure via Noise Protocol)
4. **Firewall Dependent**: Some networks block mDNS multicast traffic

## Combining mDNS with Other Discovery

Pangea Net uses **multiple discovery methods** simultaneously:

```
┌─────────────────────────────────────┐
│      Pangea Net Discovery           │
├─────────────────────────────────────┤
│                                     │
│  📡 mDNS                            │
│  └─→ Local network auto-discovery  │
│                                     │
│  🌐 DHT (Kademlia)                  │
│  └─→ Global peer discovery          │
│                                     │
│  🔗 Bootstrap Peers                 │
│  └─→ Manual connection              │
│                                     │
└─────────────────────────────────────┘
```

This means:
- Nodes on the same network find each other via mDNS
- Nodes across the internet find each other via DHT
- You can always manually connect via bootstrap peers

## Configuration

### Enable/Disable mDNS

mDNS is **always enabled** by default. It's lightweight and harmless even if no local peers exist.

If you want to disable it (not recommended):
```go
// In go/libp2p_node.go
// Comment out these lines:
// mdnsService := mdns.NewMdnsService(host, PangeaDiscoveryTopic, notifee)
```

### Change Discovery Topic

```go
// In go/libp2p_node.go
const PangeaDiscoveryTopic = "pangea-network" // Change this
```

Different topics = different isolated networks on the same LAN.

## Troubleshooting

### "No mDNS discoveries"

**Check:**
1. Are nodes on the same network?
   ```bash
   ip addr show  # Check IP addresses
   ```
2. Is multicast traffic allowed?
   ```bash
   # Check firewall
   sudo ufw status
   ```
3. Wait longer (mDNS can take 5-10 seconds)

### "mDNS discovered but connection failed"

**Check:**
1. Are ports accessible?
2. Is the Rust library loaded?
   ```bash
   export LD_LIBRARY_PATH="$PWD/rust/target/release:$LD_LIBRARY_PATH"
   ```
3. Check logs for specific error messages

### "mDNS service unavailable"

This shouldn't happen with libp2p's built-in mDNS, but if it does:
- Restart the node
- Check if multicast is supported on your network interface
- Try a different network interface

## Performance

- **Discovery Time**: 1-10 seconds (typically 2-5 seconds)
- **Bandwidth**: Minimal (~1KB/minute of multicast traffic)
- **CPU**: Negligible
- **Connections**: Automatic connection attempts are throttled to avoid overwhelming nodes

## Security

- **Discovery**: Unauthenticated (anyone on LAN can see nodes)
- **Connection**: Authenticated via Noise Protocol
- **Data**: Encrypted via Noise Protocol
- **Recommendation**: Use mDNS for testing/development, not for sensitive production deployments

## Future Enhancements

Planned improvements:
- [ ] Configurable discovery interval
- [ ] Peer filtering based on capabilities
- [ ] Service advertisements (file offerings)
- [ ] Integration with DHT for hybrid discovery

## References

- [libp2p mDNS Documentation](https://docs.libp2p.io/concepts/discovery-routing/mdns/)
- [mDNS RFC 6762](https://datatracker.ietf.org/doc/html/rfc6762)
- [Go libp2p mDNS Implementation](https://github.com/libp2p/go-libp2p/tree/master/p2p/discovery/mdns)

---

**Questions?** Check `CROSS_DEVICE_TESTING.md` for more examples, or run `./scripts/test_mdns.sh` to see it in action!

*Last Updated: 2025-11-22 | Version: 0.3.0-alpha*
