# PDF Splitter

[![CI](https://github.com/runyaga/pdf-splitter/actions/workflows/ci.yml/badge.svg)](https://github.com/runyaga/pdf-splitter/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/runyaga/pdf-splitter/branch/main/graph/badge.svg)](https://codecov.io/gh/runyaga/pdf-splitter)

A Split-Process-Merge pipeline for converting large PDFs to Docling documents. Splits PDFs into balanced chunks, processes them in parallel with Docling, then merges results into a single validated document.

## Features

- **Smart Splitting**: Auto-selects strategy based on document structure (bookmarks, chapters)
- **Parallel Processing**: Process pools for both chunking and Docling conversion
- **Document Merging**: Reassembles chunks into unified Docling document with reference integrity
- **Validation**: Verifies page coverage, provenance monotonicity, and chunk alignment
- **Memory Safe**: Process isolation prevents memory leaks on large documents

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Quick Start

```bash
# Split-Process-Merge workflow
pdf-splitter analyze document.pdf              # 1. Analyze structure
pdf-splitter chunk document.pdf -o ./chunks    # 2. Split into chunks
pdf-splitter convert ./chunks/ -o output.json  # 3. Process & merge to Docling JSON
pdf-splitter validate output.json ./chunks/    # 4. Validate merged document
```

## CLI Reference

```bash
pdf-splitter analyze <pdf>              # Show splitting recommendations
pdf-splitter chunk <pdf> -o <dir>       # Split PDF into chunks
pdf-splitter convert <dir> -o <file>    # Process chunks & merge into Docling document
pdf-splitter validate <json> <dir>      # Validate merged doc against source chunks
pdf-splitter compare <pdf>              # Compare all strategies
pdf-splitter batch <dir>                # Batch analyze directory
```

### Key Options

| Command | Option | Description |
|---------|--------|-------------|
| All | `-v` | Verbose logging |
| chunk | `-s <strategy>` | Force: `fixed`, `hybrid`, `enhanced` |
| chunk | `--max-pages N` | Max pages per chunk (default: 100) |
| chunk | `-w N` | Worker processes |
| convert | `--keep-parts` | Output individual chunks, not merged |
| convert | `--maxtasks N` | Tasks per worker before restart (default: 1) |

## Python API

```python
from src.segmentation_enhanced import smart_split, smart_split_to_files
from src.processor import BatchProcessor
from src.reassembly import merge_from_results

# 1. Analyze
result = smart_split("document.pdf", max_chunk_pages=100)
print(result.summary())

# 2. Split
chunk_paths, result = smart_split_to_files("document.pdf", output_dir="./chunks")

# 3. Process & Merge
processor = BatchProcessor(max_workers=4)
results = processor.execute_parallel(chunk_paths)
merged_doc = merge_from_results(results)  # Returns unified DoclingDocument

# 4. Export
merged_doc.export_to_json("output.json")
```

## Visualization

After merging, use [docling-view](https://github.com/runyaga/docling-view) to generate an HTML visualization of your Docling document with extracted images and bounding box overlays:

```bash
pip install docling-view
docling-view output.json -o output.html
```

## Strategies

| Strategy | Use Case |
|----------|----------|
| `fixed` | Simple documents, no bookmarks |
| `hybrid` | Documents with chapter structure |
| `enhanced` | Deep bookmark traversal |

`smart_split()` auto-selects the best strategy.

## Development

```bash
make help          # Show all commands
make install-dev   # Install dev dependencies
make lint          # Run ruff linter
make format        # Run ruff formatter
make test          # Run tests with coverage
make test-fast     # Run tests without coverage
make coverage      # Generate HTML coverage report
make quality       # Run lint + typecheck + test
make pre-commit    # Install git hooks
make clean         # Remove build artifacts
```

## Requirements

- Python 3.10+
- Dependencies: docling, pypdf
- Dev: pytest, pytest-cov, ruff, mypy, pre-commit
