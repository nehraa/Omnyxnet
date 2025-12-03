# Pangea Net Documentation Style Guide

**Version:** 1.0.0  
**Last Updated:** 2025-12-03  
**Status:** ✅ Active

## Overview

This guide establishes consistent documentation standards for the Pangea Net project. All contributors should follow these guidelines when writing or updating documentation.

## Document Structure

### Header Format

Every documentation file must start with:

```markdown
# [Document Title]

**Version:** X.Y.Z  
**Last Updated:** YYYY-MM-DD  
**Status:** [Draft | ✅ Active | ⚠️ Deprecated | ❌ Archived]
```

### Standard Sections

1. **Overview** - Brief description of what the document covers
2. **Architecture** (if applicable) - Visual diagrams and component relationships
3. **Features** - Key capabilities or concepts
4. **Quick Start** - Minimal steps to get started
5. **Detailed Documentation** - Comprehensive explanations
6. **Testing** - How to test the feature
7. **Troubleshooting** - Common issues and solutions
8. **Future Enhancements** (optional) - Roadmap items

## Formatting Conventions

### Headers

- `#` - Document title (one per document)
- `##` - Major sections
- `###` - Subsections
- `####` - Sub-subsections (use sparingly)

### Code Blocks

Always specify the language for syntax highlighting:

```rust
// Rust code
fn example() { }
```

```go
// Go code
func example() { }
```

```python
# Python code
def example():
    pass
```

```bash
# Shell commands
./run-command.sh
```

### Status Indicators

Use consistent emoji for status:

- ✅ Complete / Working / Active
- ⚠️ Partial / Warning / Deprecated
- ❌ Not working / Archived
- 🚧 In progress / Under construction
- 🚀 New / Major update
- ⏳ Pending / Waiting

### Diagrams

Use ASCII art for architecture diagrams:

```
┌─────────────────────────────────────────────────────────────┐
│                     Component Name                           │
├─────────────────────────────────────────────────────────────┤
│  Sub-component A                                             │
│  └─→ Description of relationship                            │
│                                                              │
│  Sub-component B                                             │
│  └─→ Another relationship                                   │
└─────────────────────────────────────────────────────────────┘
```

Use arrows for flow:
- `─→` Horizontal flow
- `↓` Vertical flow (downward)
- `↑` Vertical flow (upward)
- `└─→` Branch/child relationship

### Tables

Use tables for comparisons and summaries:

| Feature | Language | Status | Notes |
|---------|----------|--------|-------|
| Example | Rust     | ✅     | Working |

### Links

- Internal links: `[Link Text](path/to/file.md)`
- Section links: `[Link Text](#section-name)`
- External links: `[Link Text](https://example.com)`

## File Naming

- Use `SCREAMING_SNAKE_CASE` for documentation files: `FEATURE_NAME.md`
- Use lowercase for directories: `docs/networking/`
- Be descriptive: `DISTRIBUTED_COMPUTE.md` not `DC.md`

## Content Guidelines

### Language

- Use clear, concise language
- Prefer active voice over passive voice
- Define acronyms on first use: "WebAssembly (WASM)"
- Use consistent terminology throughout

### The Golden Rule Reference

Always reference the Golden Rule when discussing architecture:

> **Golden Rule:**
> - **Rust:** Files, memory, CES pipeline, compute sandbox
> - **Go:** All networking (libp2p, TCP, UDP, orchestration)
> - **Python:** AI, CLI management, user interface

### Code Examples

- Provide working examples that can be copy-pasted
- Include expected output when helpful
- Show both basic and advanced usage

### Version Information

When referencing features:
- Note the version where feature was introduced
- Mark deprecated features clearly
- Include migration guides for breaking changes

## Directory Structure

```
docs/
├── DOCUMENTATION_INDEX.md     # Main entry point
├── DOCUMENTATION_STYLE_GUIDE.md  # This file
├── api/                       # API documentation
│   └── CAPNP_SERVICE.md
├── networking/               # Network layer docs
│   └── NETWORK_ADAPTER.md
├── testing/                  # Testing documentation
│   └── TESTING_GUIDE.md
├── compute/                  # Distributed compute docs (NEW)
│   └── DISTRIBUTED_COMPUTE.md
└── archive/                  # Historical/deprecated docs
```

## Review Checklist

Before submitting documentation:

- [ ] Follows header format
- [ ] Includes version and date
- [ ] Has working code examples
- [ ] Uses consistent formatting
- [ ] Links are valid
- [ ] Spell-checked
- [ ] Reviewed for technical accuracy
- [ ] Cross-referenced with related docs

## Examples of Good Documentation

See these files for examples of well-formatted documentation:

- `docs/COMMUNICATION.md` - Good structure and architecture diagrams
- `docs/RUST.md` - Comprehensive technical documentation
- `docs/GOLDEN_RULE_UPDATE.md` - Clear change documentation

## Contributing

When updating documentation:

1. Follow this style guide
2. Update `docs/DOCUMENTATION_INDEX.md` for new files
3. Update the "Last Updated" date
4. Increment version if making significant changes
5. Add to changelog if applicable

---

*This style guide is a living document. Propose changes via pull requests.*
