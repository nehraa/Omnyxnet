# Archived Example Scripts

These scripts have been archived because they are replaced by newer functionality.

## Replacement Mapping

| Archived Script | Replacement |
|-----------------|-------------|
| `01_local_unit_tests.sh` | `./scripts/container_tests/test_matrix_cli.sh --local-only` |
| `02_single_node_compute.sh` | `python main.py compute matrix-multiply --generate` |
| `03_distributed_compute_initiator.sh` | `./scripts/setup.sh` → Option 2 → Manager |
| `03_distributed_compute_responder.sh` | `./scripts/setup.sh` → Option 2 → Worker |

## Why Archived?

- **Network Connection**: Now unified in `setup.sh` → Option 2 with network registry
- **Local Tests**: Now handled by containerized test suite
- **CLI Commands**: Matrix multiply now has dedicated CLI command

## If You Need These

These scripts still work but are no longer maintained. If you need them:

```bash
# Run archived script
./tests/compute/examples/archive/01_local_unit_tests.sh
```

## Recommended Alternatives

```bash
# Local matrix multiplication
python main.py compute matrix-multiply --size 10 --generate --verify

# Network connection (Manager)
./scripts/setup.sh  # Select Option 2 → Manager

# Network connection (Worker)
./scripts/setup.sh  # Select Option 2 → Worker

# Containerized testing
./scripts/run_container_tests.sh --quick
```

See [docs/CLI_MATRIX_MULTIPLY.md](../../../../docs/CLI_MATRIX_MULTIPLY.md) for the new CLI reference.
