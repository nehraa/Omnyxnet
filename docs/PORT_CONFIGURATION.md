# Port Configuration Reference

This document provides a centralized reference for all ports used in the Pangea Net system.

## Default Port Assignments

### Core Services

| Service | Port | Purpose | Configurable Via | Default |
|---------|------|---------|------------------|---------|
| Go Node RPC | 8080 | Cap'n Proto RPC Server | `-capnp-addr` flag / `GO_NODE_PORT` env | `:8080` |
| Demo Server | 8000 | FastAPI Web Server | `DEMO_PORT` env | `8000` |
| libp2p P2P (Node 1) | 9081 | P2P Network Communication | `-libp2p-port` flag | `9081` |
| libp2p P2P (Node 2) | 9082 | P2P Network Communication | `-libp2p-port` flag | `9082` |
| libp2p P2P (Node 3) | 9083 | P2P Network Communication | `-libp2p-port` flag | `9083` |
| libp2p P2P (Node 4) | 9084 | P2P Network Communication | `-libp2p-port` flag | `9084` |

### Docker Container Ports

When running in Docker, ports are mapped as follows:

**2-Node Configuration** (`docker-compose.test.2node.yml`):
- Manager: `8080:8080` (RPC), `9081:9081` (P2P)
- Worker: `8081:8080` (RPC), `9082:9082` (P2P)

**3-Node Configuration** (`docker-compose.test.3node.yml`):
- Node 1: `8080:8080` (RPC), `9081:9081` (P2P)
- Node 2: `8081:8080` (RPC), `9082:9082` (P2P)
- Node 3: `8082:8080` (RPC), `9083:9083` (P2P)

**Compute Cluster** (`docker-compose.test.compute.yml`):
- Manager: `8080:8080` (RPC), `9081:9081` (P2P)
- Worker 1: `8081:8080` (RPC), `9082:9082` (P2P)
- Worker 2: `8082:8080` (RPC), `9083:9083` (P2P)
- Worker 3: `8083:8080` (RPC), `9084:9084` (P2P)

## Port Conflict Resolution

If you encounter port conflicts with other services on your system, you can change ports using:

### For Go Node
```bash
# Change RPC port
./go/bin/go-node -capnp-addr=:8090 -libp2p-port=9091

# Or use environment variable
export GO_NODE_PORT=8090
./go/bin/go-node
```

### For Demo Server
```bash
# Change demo port
export DEMO_PORT=8001
./setup.sh --demo
```

### For Docker Compose
Edit the respective `docker-compose.test.*.yml` file and change the port mappings:

```yaml
ports:
  - "8090:8080"  # Change host port (8090) but keep container port (8080)
  - "9091:9081"  # Change host port (9091) but keep container port (9081)
```

## Common Port Conflicts

### Port 8080
8080 is commonly used by:
- Apache Tomcat
- Jenkins CI
- HTTP proxy servers
- Alternative HTTP servers

**Solution**: Use `-capnp-addr=:8090` or another unused port

### Port 8000
8000 is commonly used by:
- Django development server
- Python HTTP server (`python -m http.server`)
- Alternative web frameworks

**Solution**: Use `export DEMO_PORT=8001` or another unused port

### Port 9081-9084
These ports are less commonly used but may conflict with:
- Custom P2P applications
- Database clusters
- Monitoring services

**Solution**: Use `-libp2p-port=9091` (or similar) for each node

## Checking for Port Availability

Before starting services, check if ports are available:

### Linux/macOS
```bash
# Check if port 8080 is in use
lsof -i :8080

# Check multiple ports
for port in 8080 8000 9081 9082; do
  if lsof -i :$port > /dev/null 2>&1; then
    echo "Port $port is IN USE"
  else
    echo "Port $port is available"
  fi
done
```

### Windows
```powershell
# Check if port 8080 is in use
netstat -ano | findstr :8080
```

## Port Range Allocation

To avoid conflicts, Pangea Net uses the following port ranges:

- **8000-8099**: Application-level services (RPC, web servers)
- **9000-9099**: P2P networking (libp2p)
- **7000-7099**: Reserved for future use (DHT, discovery services)

## Best Practices

1. **Check before starting**: Always verify ports are available before starting services
2. **Use environment variables**: Configure ports via environment variables for flexibility
3. **Document changes**: If you change default ports, update your deployment documentation
4. **Avoid privileged ports**: Don't use ports < 1024 (requires root/admin privileges)
5. **Keep services separate**: Use different port ranges for different service types

## Troubleshooting

### "Address already in use" Error
This means the port is already being used by another service. Options:
1. Stop the other service using the port
2. Change Pangea Net to use a different port
3. Kill the process using the port (find with `lsof -i :PORT`)

### Docker Port Binding Issues
If Docker can't bind ports:
1. Check if host ports are available
2. Ensure Docker daemon is running
3. Try different host port mappings
4. Check firewall settings

### mDNS Discovery Not Working
If nodes can't discover each other:
1. Verify nodes are on the same network
2. Check firewall allows mDNS (port 5353 UDP)
3. Ensure `-local` flag is set for local testing
4. Check container network configuration

## Security Considerations

- **Expose only necessary ports**: Don't expose internal ports to public networks
- **Use firewalls**: Configure firewalls to restrict port access
- **Monitor port usage**: Regularly audit which ports are exposed
- **Encrypt connections**: All P2P communication uses encryption (Noise Protocol)

## Related Documentation

- [Docker Compose Configuration](docker-compose.test.compute.yml)
- [Go Node Setup](go/README.md)
- [Demo Server](demo/server.py)
- [Network Connection Guide](docs/NETWORK_CONNECTION.md)
