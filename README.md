# PDF Splitter

A scalable PDF splitting framework for parallel document processing using Docling. Intelligently splits large PDFs into balanced chunks while respecting document structure (chapters, sections, bookmarks).

## Features

- **Smart Splitting**: Auto-selects the best strategy based on document structure
- **Bookmark-Aware**: Respects chapter/section boundaries when available
- **Balanced Chunks**: Ensures no single chunk dominates (prevents 1000+ page chunks)
- **Parallel I/O**: Writes chunk files in parallel using thread pool
- **Parallel Processing**: Docling conversion with process pool and memory isolation
- **Memory Safe**: `maxtasksperchild=1` prevents ~1GB/chunk memory leaks

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

# Create PDF chunks (parallel by default)
pdf-splitter chunk document.pdf --output ./chunks
pdf-splitter chunk document.pdf --workers 8 --output ./chunks

# Convert chunks to structured documents (parallel Docling)
pdf-splitter convert ./chunks/
pdf-splitter convert ./chunks/ --workers 4 --output results.json

# Compare all splitting strategies
pdf-splitter compare document.pdf

# Batch analyze a directory
pdf-splitter batch ./documents/
```

### CLI Options

```bash
# Chunk options:
#   -o, --output DIR    Output directory
#   -s, --strategy STR  Force strategy: fixed, hybrid, enhanced
#   -w, --workers N     Parallel write workers (default: CPU count)
#   --sequential        Disable parallel writing
#   --max-pages N       Maximum pages per chunk (default: 100)
#   --min-pages N       Minimum pages per chunk (default: 15)
#   --overlap N         Overlap pages between chunks (default: 0)
#   -v, --verbose       Show [BEGIN]/[COMPLETE] lifecycle per chunk

# Convert options:
#   -o, --output FILE   Output JSON file for Docling results
#   -w, --workers N     Parallel Docling workers (default: CPU count)
#   --maxtasks N        Tasks per worker before restart (default: 1)
#   -v, --verbose       Show conversion details
```

### When to Use Each Command

| Command | Use Case | Example |
|---------|----------|---------|
| `analyze` | Understand a PDF's structure before splitting | You have a 1000-page manual and want to see how it's organized (bookmarks, chapters) before deciding on chunk sizes |
| `chunk` | Create smaller PDF files from a large document | You need to break a 500-page PDF into 50-page chunks for parallel processing or to stay within API limits |
| `convert` | Extract structured content (text, tables) from PDFs | You have PDF chunks and need to extract their content as structured data for an LLM pipeline or search index |
| `compare` | Evaluate different splitting strategies | You're unsure whether bookmark-based or fixed-size splitting works better for your document type |
| `batch` | Analyze multiple PDFs at once | You have a directory of PDFs and want a quick overview of how each would be split |

**Typical Workflow:**
```bash
# 1. Analyze the document structure
pdf-splitter analyze large_manual.pdf --verbose

# 2. Create chunks (uses ThreadPoolExecutor - single process, multiple threads)
pdf-splitter chunk large_manual.pdf --output ./chunks --max-pages 50

# 3. Convert chunks to structured documents (uses ProcessPoolExecutor - multiple processes)
pdf-splitter convert ./chunks/ --output results.json --workers 8
```

**Why Two Separate Commands?**
- `chunk` uses **threads** for fast I/O-bound PDF writing (single Python process)
- `convert` uses **processes** for CPU-bound Docling extraction (multiple Python processes with memory isolation)

### Python API

```python
from src.segmentation_enhanced import smart_split, smart_split_to_files
from src.processor import BatchProcessor

# Analyze and get chunk boundaries
result = smart_split("document.pdf", max_chunk_pages=100)
print(result.summary())
# Strategy: auto_hybrid_chapter_l4
# Total pages: 981
# Chunks: 20
# Chunk sizes: 10-101 pages (avg 49.8)

# Create chunk files (parallel by default)
chunk_paths, result = smart_split_to_files(
    "document.pdf",
    output_dir="./chunks",
    max_chunk_pages=100,
    max_workers=8,        # parallel write workers
    parallel=True         # set False for sequential
)

# Convert chunks with Docling (parallel)
processor = BatchProcessor(max_workers=4, maxtasksperchild=1)
results = processor.execute_parallel(chunk_paths)
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
