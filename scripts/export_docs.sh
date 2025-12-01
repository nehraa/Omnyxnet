#!/bin/bash
# Export all documentation to Desktop
# Creates both individual files and a combined documentation file

set -e

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Configuration
DESKTOP="$HOME/Desktop"
OUTPUT_DIR="$DESKTOP/WGT-Documentation-$(date +%Y%m%d-%H%M%S)"
COMBINED_FILE="$OUTPUT_DIR/COMPLETE_DOCUMENTATION.md"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   WGT Documentation Export Tool       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"
echo -e "${GREEN}✓${NC} Created: $OUTPUT_DIR"

# Find all markdown files (excluding venv, node_modules, etc.)
echo -e "${BLUE}Searching for documentation files...${NC}"
MD_FILES=$(find . -name "*.md" \
    -not -path "*/node_modules/*" \
    -not -path "*/.git/*" \
    -not -path "*/target/*" \
    -not -path "*/venv/*" \
    -not -path "*/.venv/*" \
    -not -path "*/._*" \
    -type f | sort)
FILE_COUNT=$(echo "$MD_FILES" | wc -l)
echo -e "${GREEN}✓${NC} Found $FILE_COUNT markdown files"
echo ""

# Copy individual files with organized structure
echo -e "${BLUE}Copying individual files...${NC}"
for file in $MD_FILES; do
    # Create relative directory structure
    rel_path=${file#./}
    dest_dir="$OUTPUT_DIR/$(dirname "$rel_path")"
    mkdir -p "$dest_dir"
    cp "$file" "$dest_dir/"
    echo "  ✓ $rel_path"
done
echo ""

# Create combined documentation file
echo -e "${BLUE}Creating combined documentation...${NC}"
cat > "$COMBINED_FILE" << 'EOF'
# WGT - Complete Documentation
**Generated:** $(date '+%Y-%m-%d %H:%M:%S')

This document contains all project documentation in a single file for easy reference.

---

# Table of Contents

EOF

# Build table of contents
TOC_NUMBER=1
for file in $MD_FILES; do
    title=$(basename "$file" .md | tr '_' ' ' | sed 's/\b\(.\)/\u\1/g')
    echo "$TOC_NUMBER. [$title](#$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-'))" >> "$COMBINED_FILE"
    TOC_NUMBER=$((TOC_NUMBER + 1))
done

echo "" >> "$COMBINED_FILE"
echo "---" >> "$COMBINED_FILE"
echo "" >> "$COMBINED_FILE"

# Append all files
for file in $MD_FILES; do
    title=$(basename "$file" .md | tr '_' ' ' | sed 's/\b\(.\)/\u\1/g')
    rel_path=${file#./}
    
    echo "" >> "$COMBINED_FILE"
    echo "# $title" >> "$COMBINED_FILE"
    echo "" >> "$COMBINED_FILE"
    echo "_Source: \`$rel_path\`_" >> "$COMBINED_FILE"
    echo "" >> "$COMBINED_FILE"
    
    # Append file content, adjusting heading levels (skip if file has encoding issues)
    if file "$file" | grep -q "text"; then
        cat "$file" | LC_ALL=C sed 's/^# /## /g; s/^## /### /g; s/^### /#### /g' >> "$COMBINED_FILE" 2>/dev/null || echo "_(Could not process file content)_" >> "$COMBINED_FILE"
    else
        echo "_(Binary or encoded file - skipped)_" >> "$COMBINED_FILE"
    fi
    
    echo "" >> "$COMBINED_FILE"
    echo "---" >> "$COMBINED_FILE"
    echo "" >> "$COMBINED_FILE"
done

echo -e "${GREEN}✓${NC} Combined documentation created"
echo ""

# Create index file
INDEX_FILE="$OUTPUT_DIR/INDEX.md"
cat > "$INDEX_FILE" << EOF
# WGT Documentation Index

**Export Date:** $(date '+%Y-%m-%d %H:%M:%S')  
**Total Files:** $FILE_COUNT

## Quick Links

- [Complete Documentation (Single File)](./COMPLETE_DOCUMENTATION.md)
- [Individual Files (Organized Structure)](./.)

## Documentation Structure

### Root Documentation
EOF

# List root-level docs
for file in $MD_FILES; do
    if [ "$(dirname "$file")" = "." ]; then
        basename "$file"
    fi
done | sort | while read fname; do
    title=$(basename "$fname" .md | tr '_' ' ')
    echo "- [$title](./$fname)" >> "$INDEX_FILE"
done

# List by directory
for dir in $(find . -name "*.md" -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/target/*" -not -path "*/venv/*" -not -path "*/.venv/*" | sed 's|/[^/]*$||' | sort -u | grep -v "^\.$"); do
    dir_name=$(basename "$dir")
    dir_name_cap=$(echo "$dir_name" | sed 's/\b\(.\)/\u\1/g')
    echo "" >> "$INDEX_FILE"
    echo "### $dir_name_cap" >> "$INDEX_FILE"
    find "$dir" -maxdepth 1 -name "*.md" | sort | while read file; do
        fname=$(basename "$file")
        title=$(basename "$fname" .md | tr '_' ' ')
        rel_path=${file#./}
        echo "- [$title](./$rel_path)" >> "$INDEX_FILE"
    done
done

cat >> "$INDEX_FILE" << EOF

## Documentation Files by Category

### Setup & Getting Started
- docs/START_HERE.md
- docs/QUICK_START.md
- docs/SETUP_GUIDE.md
- docs/TESTING_QUICK_START.md

### Implementation & Architecture
- README.md
- DOCUMENTATION_INDEX.md
- docs/ARCHITECTURE.md
- docs/BLUEPRINT_IMPLEMENTATION.md

### Testing & Cross-Device
- CROSS_DEVICE_TESTING.md
- docs/testing/TESTING_GUIDE.md

### Security
- SECURITY.md

### API Documentation
- docs/PYTHON_API.md
- docs/api/CAPNP_SERVICE.md

### Status & Changelog
- STATUS_SUMMARY.md
- VERSION.md
- WORK_COMPLETE_NOV22.md

---

**Export Location:** \`$OUTPUT_DIR\`
EOF

echo -e "${GREEN}✓${NC} Index file created"
echo ""

# Create README for the export
cat > "$OUTPUT_DIR/README.md" << EOF
# WGT Documentation Export

**Export Date:** $(date '+%Y-%m-%d %H:%M:%S')  
**Total Documentation Files:** $FILE_COUNT

## Contents

1. **COMPLETE_DOCUMENTATION.md** - All documentation in a single file
2. **INDEX.md** - Organized index with links to all documents
3. **Organized folders** - Original directory structure preserved

## Quick Start

- For a complete overview: Open [COMPLETE_DOCUMENTATION.md](./COMPLETE_DOCUMENTATION.md)
- For specific topics: Use [INDEX.md](./INDEX.md) to navigate
- To browse by structure: Navigate the folder tree

## Project Information

**WGT (Wireless Golden Triangle)**  
A decentralized P2P file storage system using:
- Go (Soldier) - Network transport layer
- Rust (Worker) - CES pipeline (Compress, Encrypt, Shard)
- Python (Manager) - AI threat detection & orchestration

For more information, see README.md in this directory.

---

Exported from: \`$(pwd)\`
EOF

# Generate statistics file
STATS_FILE="$OUTPUT_DIR/DOCUMENTATION_STATS.txt"
cat > "$STATS_FILE" << EOF
WGT Documentation Statistics
Generated: $(date '+%Y-%m-%d %H:%M:%S')

Total Documentation Files: $FILE_COUNT

File Sizes:
EOF

find "$OUTPUT_DIR" -name "*.md" -exec wc -l {} + | sort -rn >> "$STATS_FILE"

echo "" >> "$STATS_FILE"
echo "Total Lines:" >> "$STATS_FILE"
find "$OUTPUT_DIR" -name "*.md" -exec cat {} + | wc -l >> "$STATS_FILE"

echo "" >> "$STATS_FILE"
echo "Total Words:" >> "$STATS_FILE"
find "$OUTPUT_DIR" -name "*.md" -exec cat {} + | wc -w >> "$STATS_FILE"

# Summary
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Export Complete!${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}📂 Location:${NC} $OUTPUT_DIR"
echo -e "${YELLOW}📄 Files Exported:${NC} $FILE_COUNT markdown files"
echo ""
echo -e "${BLUE}📖 Quick Access:${NC}"
echo "   1. Complete Documentation: $OUTPUT_DIR/COMPLETE_DOCUMENTATION.md"
echo "   2. Index: $OUTPUT_DIR/INDEX.md"
echo "   3. README: $OUTPUT_DIR/README.md"
echo ""
echo -e "${GREEN}Opening in Finder...${NC}"
open "$OUTPUT_DIR"

