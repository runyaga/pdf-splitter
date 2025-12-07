#!/usr/bin/env python3
"""
PDF Splitter CLI

Command-line interface for smart PDF splitting.

Usage:
    python -m src.cli analyze <pdf_path>
    python -m src.cli split <pdf_path> [--output <dir>] [--max-pages <n>]
    python -m src.cli compare <pdf_path>
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from src.logging_config import setup_logging


def cmd_analyze(args):
    """Analyze a PDF and show splitting recommendations."""
    from src.segmentation_enhanced import smart_split, analyze_document_structure

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        return 1

    error = _validate_options(args)
    if error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"{'='*70}")
    print(f"ANALYZING: {pdf_path.name}")
    print(f"{'='*70}")

    # Get file info
    size_mb = pdf_path.stat().st_size / (1024 * 1024)
    print(f"File size: {size_mb:.2f} MB")

    # Analyze structure
    analysis = analyze_document_structure(pdf_path)
    print(f"Total pages: {analysis['total_pages']}")
    print(f"Has bookmarks: {analysis['has_outline']}")

    if analysis['bookmark_levels']:
        print(f"\nBookmark Structure:")
        for level, info in sorted(analysis['bookmark_levels'].items()):
            print(f"  Level {level}: {info['count']} items ({info['unique_pages']} unique pages)")
            if args.verbose and info['sample_titles']:
                for title in info['sample_titles'][:3]:
                    print(f"    - {title[:55]}...")

    # Get smart split result
    result = smart_split(
        pdf_path,
        max_chunk_pages=args.max_pages,
        min_chunk_pages=args.min_pages,
        overlap=args.overlap
    )

    print(f"\n{'='*70}")
    print("SMART SPLIT RESULT")
    print(f"{'='*70}")
    print(result.summary())

    if args.verbose:
        print(f"\nChunk Details:")
        for i, (start, end) in enumerate(result.boundaries):
            pages = end - start
            print(f"  {i+1:3d}: pages {start+1:5d} - {end:5d} ({pages:4d} pages)")

    return 0


def cmd_split(args):
    """Split a PDF into chunks."""
    from src.segmentation_enhanced import smart_split_to_files

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        return 1

    error = _validate_options(args)
    if error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    output_dir = Path(args.output) if args.output else None

    print(f"Splitting: {pdf_path.name}")
    print(f"Max chunk size: {args.max_pages} pages")
    if output_dir:
        print(f"Output directory: {output_dir}")

    # Perform split
    chunk_paths, result = smart_split_to_files(
        pdf_path,
        output_dir=output_dir,
        max_chunk_pages=args.max_pages,
        min_chunk_pages=args.min_pages,
        overlap=args.overlap,
        force_strategy=args.strategy
    )

    print(f"\n{result.summary()}")
    print(f"\nCreated {len(chunk_paths)} chunk files:")

    if output_dir is None and chunk_paths:
        output_dir = chunk_paths[0].parent

    total_size = 0
    for path in chunk_paths:
        size_kb = path.stat().st_size / 1024
        total_size += size_kb
        if args.verbose:
            print(f"  {path.name} ({size_kb:.1f} KB)")

    print(f"\nOutput directory: {output_dir}")
    print(f"Total size: {total_size/1024:.2f} MB")

    return 0


def cmd_compare(args):
    """Compare all splitting strategies on a PDF."""
    from src.segmentation import get_split_boundaries
    from src.segmentation_enhanced import (
        get_split_boundaries_enhanced,
        get_split_boundaries_hybrid,
        smart_split
    )
    from pypdf import PdfReader

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        return 1

    error = _validate_options(args)
    if error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)

    print(f"{'='*75}")
    print(f"STRATEGY COMPARISON: {pdf_path.name} ({total} pages)")
    print(f"{'='*75}")

    # Original
    b1 = get_split_boundaries(pdf_path, chunk_size=args.max_pages, overlap=args.overlap)
    sizes1 = [e-s for s,e in b1] if b1 else [0]

    # Enhanced
    b2, strat2 = get_split_boundaries_enhanced(pdf_path, args.max_pages, args.overlap)
    sizes2 = [e-s for s,e in b2] if b2 else [0]

    # Hybrid
    b3, strat3 = get_split_boundaries_hybrid(pdf_path, args.max_pages, args.min_pages, args.overlap)
    sizes3 = [e-s for s,e in b3] if b3 else [0]

    # Smart (auto)
    result = smart_split(pdf_path, args.max_pages, args.min_pages, args.overlap)

    print(f"\n{'Strategy':<35} {'Chunks':>7} {'Min':>6} {'Max':>6} {'Avg':>8}")
    print(f"{'-'*35} {'-'*7} {'-'*6} {'-'*6} {'-'*8}")

    print(f"{'Original (basic)':<35} {len(b1):>7} {min(sizes1):>6} {max(sizes1):>6} {sum(sizes1)/len(sizes1):>8.1f}")
    print(f"{'Enhanced (' + strat2[:20] + ')':<35} {len(b2):>7} {min(sizes2):>6} {max(sizes2):>6} {sum(sizes2)/len(sizes2):>8.1f}")
    print(f"{'Hybrid (' + strat3[:23] + ')':<35} {len(b3):>7} {min(sizes3):>6} {max(sizes3):>6} {sum(sizes3)/len(sizes3):>8.1f}")
    print(f"{'-'*35} {'-'*7} {'-'*6} {'-'*6} {'-'*8}")
    print(f"{'>>> Smart Auto (' + result.strategy[:15] + ')':<35} {result.num_chunks:>7} {result.min_chunk_size:>6} {result.max_chunk_size:>6} {result.avg_chunk_size:>8.1f}")

    # Recommendation
    print(f"\nRecommendation: smart_split() selected '{result.strategy}'")

    return 0


def cmd_batch(args):
    """Process all PDFs in a directory."""
    from src.segmentation_enhanced import smart_split

    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        print(f"Error: Not a directory: {input_dir}", file=sys.stderr)
        return 1

    error = _validate_options(args)
    if error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    pdfs = list(input_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {input_dir}")
        return 0

    print(f"{'='*75}")
    print(f"BATCH ANALYSIS: {len(pdfs)} PDFs")
    print(f"{'='*75}")

    print(f"\n{'PDF':<30} {'Pages':>7} {'Chunks':>7} {'Max':>6} {'Strategy':<20}")
    print(f"{'-'*30} {'-'*7} {'-'*7} {'-'*6} {'-'*20}")

    for pdf_path in sorted(pdfs):
        try:
            result = smart_split(pdf_path, args.max_pages, args.min_pages, args.overlap)
            print(f"{pdf_path.name[:29]:<30} {result.total_pages:>7} {result.num_chunks:>7} {result.max_chunk_size:>6} {result.strategy[:19]:<20}")
        except Exception as e:
            print(f"{pdf_path.name[:29]:<30} ERROR: {str(e)[:40]}")

    return 0


def _add_common_options(parser):
    """Add common splitting options to a parser."""
    parser.add_argument("--max-pages", type=int, default=100,
                        help="Maximum pages per chunk (default: 100)")
    parser.add_argument("--min-pages", type=int, default=15,
                        help="Minimum pages per chunk (default: 15)")
    parser.add_argument("--overlap", type=int, default=0,
                        help="Overlap pages between chunks (default: 0)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output")


def _validate_options(args):
    """Validate common options, returns error message or None."""
    if args.max_pages < 1:
        return f"--max-pages must be >= 1, got {args.max_pages}"
    if args.min_pages < 1:
        return f"--min-pages must be >= 1, got {args.min_pages}"
    if args.overlap < 0:
        return f"--overlap must be >= 0, got {args.overlap}"
    return None


def main():
    parser = argparse.ArgumentParser(
        description="PDF Splitter - Smart PDF chunking for parallel processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Analyze a PDF:
    pdf-splitter analyze document.pdf
    pdf-splitter analyze document.pdf --verbose

  Split a PDF:
    pdf-splitter split document.pdf --output ./chunks
    pdf-splitter split document.pdf --max-pages 50 --strategy fixed

  Compare strategies:
    pdf-splitter compare document.pdf

  Batch analyze:
    pdf-splitter batch ./documents/
"""
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # analyze command
    p_analyze = subparsers.add_parser("analyze", help="Analyze PDF structure")
    p_analyze.add_argument("pdf", help="Path to PDF file")
    _add_common_options(p_analyze)
    p_analyze.set_defaults(func=cmd_analyze)

    # split command
    p_split = subparsers.add_parser("split", help="Split PDF into chunks")
    p_split.add_argument("pdf", help="Path to PDF file")
    p_split.add_argument("-o", "--output", help="Output directory")
    p_split.add_argument("-s", "--strategy", choices=["fixed", "hybrid", "enhanced"],
                         help="Force specific strategy")
    _add_common_options(p_split)
    p_split.set_defaults(func=cmd_split)

    # compare command
    p_compare = subparsers.add_parser("compare", help="Compare splitting strategies")
    p_compare.add_argument("pdf", help="Path to PDF file")
    _add_common_options(p_compare)
    p_compare.set_defaults(func=cmd_compare)

    # batch command
    p_batch = subparsers.add_parser("batch", help="Analyze all PDFs in directory")
    p_batch.add_argument("input_dir", help="Directory containing PDFs")
    _add_common_options(p_batch)
    p_batch.set_defaults(func=cmd_batch)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Configure logging based on verbosity
    setup_logging(verbose=args.verbose)

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
