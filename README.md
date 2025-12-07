# PDF Splitter

A scalable PDF splitting framework for parallel document processing using Docling. Intelligently splits large PDFs into balanced chunks while respecting document structure (chapters, sections, bookmarks).

## Features

- **Smart Splitting**: Auto-selects best strategy based on document structure
- **Bookmark-Aware**: Respects chapter/section boundaries
- **Parallel Processing**: Process pools for chunking and Docling conversion
- **Image Extraction**: Preserves page images and embedded figures
- **Memory Safe**: `maxtasksperchild=1` prevents memory leaks

## Installation

```bash
# Using uv (recommended)
uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"

# Using pip
python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
```

## Usage

```bash
pdf-splitter analyze document.pdf           # Analyze structure
pdf-splitter chunk document.pdf -o ./chunks # Create chunks
pdf-splitter convert ./chunks/ -o docling.json  # Convert to JSON
pdf-splitter validate docling.json ./chunks/    # Validate output
pdf-splitter compare document.pdf           # Compare strategies
pdf-splitter batch ./documents/             # Batch analyze
```

### CLI Options

```bash
# Common options:
#   -v, --verbose       Enable INFO logging (default: WARNING, quiet)

# Chunk options:
#   -o, --output DIR    Output directory
#   -s, --strategy STR  Force strategy: fixed, hybrid, enhanced
#   -w, --workers N     Parallel processes (default: 80% of CPUs)
#   --sequential        Disable parallel writing
#   --max-pages N       Max pages per chunk (default: 100)
#   --min-pages N       Min pages per chunk (default: 15)

# Convert options:
#   -o, --output FILE   Output JSON file
#   -w, --workers N     Parallel processes (default: 80% of CPUs)
#   --maxtasks N        Tasks per worker before restart (default: 1)

# Validate options:
#   -v, --verbose       Show per-chunk details
```

### Workflow

```bash
pdf-splitter analyze document.pdf -v              # 1. Analyze
pdf-splitter chunk document.pdf -o ./chunks       # 2. Chunk
pdf-splitter convert ./chunks/ -o docling.json    # 3. Convert
pdf-splitter validate docling.json ./chunks/      # 4. Validate
```

### Python API

```python
from src.segmentation_enhanced import smart_split, smart_split_to_files
from src.processor import BatchProcessor

# Analyze
result = smart_split("document.pdf", max_chunk_pages=100)
print(result.summary())

# Create chunks
chunk_paths, result = smart_split_to_files("document.pdf", output_dir="./chunks")

# Convert with Docling
processor = BatchProcessor(max_workers=4)
results = processor.execute_parallel(chunk_paths)
```

## Strategies

| Strategy | Use Case |
|----------|----------|
| `fixed` | Simple documents, no bookmarks |
| `hybrid` | Documents with chapter structure |
| `enhanced` | Deep bookmark traversal |

`smart_split()` auto-selects the best strategy.

## Tests

```bash
pytest tests/ -v
```

## Requirements

- Python 3.10+
- docling, pypdf
