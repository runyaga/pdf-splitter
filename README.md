# PDF Splitter

A scalable PDF splitting framework for parallel document processing using Docling. Intelligently splits large PDFs into balanced chunks while respecting document structure (chapters, sections, bookmarks).

## Features

- **Smart Splitting**: Auto-selects the best strategy based on document structure
- **Bookmark-Aware**: Respects chapter/section boundaries when available
- **Balanced Chunks**: Ensures no single chunk dominates (prevents 1000+ page chunks)
- **Parallel Processing**: Designed for use with Docling's parallel document conversion
- **Memory Safe**: Process isolation prevents memory leaks in long-running jobs

## Installation

### Using uv (recommended)

```bash
# Create virtual environment and install
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Using pip

```bash
# Create virtual environment and install
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Legacy (requirements.txt)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

### CLI Usage

```bash
# Analyze a PDF's structure
pdf-splitter analyze document.pdf

# Split a PDF into chunks
pdf-splitter split document.pdf --output ./chunks

# Compare all splitting strategies
pdf-splitter compare document.pdf

# Batch analyze a directory
pdf-splitter batch ./documents/
```

### CLI Options

```bash
pdf-splitter split --help

# Options (available on all subcommands):
#   --max-pages N    Maximum pages per chunk (default: 100)
#   --min-pages N    Minimum pages per chunk (default: 15)
#   --overlap N      Overlap pages between chunks (default: 5)
#   -v, --verbose    Show detailed progress (chunk writes, strategy decisions)

# Split-specific options:
#   -o, --output     Output directory
#   -s, --strategy   Force strategy: fixed, hybrid, enhanced
```

### Python API

```python
from src.segmentation_enhanced import smart_split, smart_split_to_files

# Analyze and get split boundaries
result = smart_split("document.pdf", max_chunk_pages=100)
print(result.summary())
# Strategy: auto_hybrid_chapter_l4
# Total pages: 981
# Chunks: 20
# Chunk sizes: 10-101 pages (avg 49.8)

# Split to files
chunk_paths, result = smart_split_to_files(
    "document.pdf",
    output_dir="./chunks",
    max_chunk_pages=100
)
```

## Splitting Strategies

| Strategy | Use Case |
|----------|----------|
| `single_chunk` | Small documents (< max_chunk_pages) |
| `fixed` | No bookmarks or simple documents |
| `hybrid` | Complex documents with chapter structure |
| `enhanced` | Deep bookmark traversal with auto-level detection |

The `smart_split()` function automatically selects the best strategy.

## Running Tests

```bash
# Run all unit tests
pytest tests/ -v --ignore=tests/test_integration.py

# Run integration tests (requires PDFs in assets/)
pytest tests/ -v -m integration

# Run all tests
pytest tests/ -v
```

## Project Structure

```
pdf-splitter/
├── pyproject.toml             # Project configuration
├── src/
│   ├── cli.py                 # CLI implementation
│   ├── segmentation.py        # Basic splitting
│   ├── segmentation_enhanced.py  # Smart splitting strategies
│   ├── config_factory.py      # Docling converter config
│   ├── processor.py           # Parallel batch processing
│   └── reassembly.py          # Document merging
├── tests/                     # Test suite
└── assets/                    # Place PDFs here
```

## Requirements

- Python 3.10+
- docling
- pypdf
- pytest (for testing)
