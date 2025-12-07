#!/usr/bin/env python3
"""
Validate DoclingDocument output against source chunks.

Usage: python validate_docling_output.py [docling_json] [chunks_dir]

Defaults:
  - docling_json: as-docling.json
  - chunks_dir: assets/output
"""

import json
import sys
import re
from pathlib import Path
from collections import defaultdict


def parse_chunk_filename(filename: str) -> tuple[int, int, int]:
    """
    Extract chunk index and page range from filename.

    Example: chunk_0000_pages_0001_0034.pdf -> (0, 1, 34)
    """
    match = re.match(r'chunk_(\d+)_pages_(\d+)_(\d+)\.pdf', filename)
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return None, None, None


def extract_provenance_pages(document_dict: dict) -> list[int]:
    """
    Extract all page numbers from provenance data in the document.
    """
    pages = set()

    # Check texts
    for text in document_dict.get('texts', []):
        for prov in text.get('prov', []):
            if 'page_no' in prov:
                pages.add(prov['page_no'])

    # Check tables
    for table in document_dict.get('tables', []):
        for prov in table.get('prov', []):
            if 'page_no' in prov:
                pages.add(prov['page_no'])

    # Check pictures
    for pic in document_dict.get('pictures', []):
        for prov in pic.get('prov', []):
            if 'page_no' in prov:
                pages.add(prov['page_no'])

    return sorted(pages)


def validate_chunk(chunk_result: dict, chunks_dir: Path) -> dict:
    """
    Validate a single chunk result.

    Returns dict with validation results.

    Note: Provenance page numbers are RELATIVE to the chunk (1-based),
    not absolute to the original document. Each chunk is a standalone PDF.
    """
    issues = []
    chunk_path = chunk_result.get('chunk_path', '')
    chunk_name = Path(chunk_path).name

    # Parse expected page range from filename
    chunk_idx, start_page, end_page = parse_chunk_filename(chunk_name)

    if chunk_idx is None:
        issues.append(f"Could not parse chunk filename: {chunk_name}")
        return {'chunk': chunk_name, 'valid': False, 'issues': issues}

    # Calculate expected chunk length
    chunk_page_count = end_page - start_page + 1

    # Check if chunk file exists
    chunk_file = chunks_dir / chunk_name
    if not chunk_file.exists():
        issues.append(f"Chunk file not found: {chunk_file}")

    # Check success flag
    if not chunk_result.get('success'):
        error = chunk_result.get('error', 'Unknown error')
        issues.append(f"Processing failed: {error}")
        return {
            'chunk': chunk_name,
            'chunk_idx': chunk_idx,
            'original_pages': (start_page, end_page),
            'chunk_page_count': chunk_page_count,
            'valid': False,
            'issues': issues
        }

    doc_dict = chunk_result.get('document_dict', {})
    if not doc_dict:
        issues.append("No document_dict in result")
        return {
            'chunk': chunk_name,
            'chunk_idx': chunk_idx,
            'original_pages': (start_page, end_page),
            'chunk_page_count': chunk_page_count,
            'valid': False,
            'issues': issues
        }

    # Extract provenance pages (these are 1-based relative to chunk)
    prov_pages = extract_provenance_pages(doc_dict)

    # Expected pages in chunk coordinate system: 1 to chunk_page_count
    expected_chunk_pages = set(range(1, chunk_page_count + 1))
    actual_pages = set(prov_pages)

    missing_pages = expected_chunk_pages - actual_pages
    extra_pages = actual_pages - expected_chunk_pages

    if missing_pages:
        # Only warn if significant portion missing
        if len(missing_pages) > chunk_page_count * 0.1:  # >10% missing
            issues.append(f"Missing {len(missing_pages)}/{chunk_page_count} pages in provenance")

    if extra_pages:
        # Pages outside expected range - shouldn't happen
        issues.append(f"Pages outside chunk range: {sorted(extra_pages)}")

    # Check page coverage percentage
    coverage = len(actual_pages & expected_chunk_pages) / chunk_page_count * 100 if chunk_page_count > 0 else 0

    # Count document elements
    num_texts = len(doc_dict.get('texts', []))
    num_tables = len(doc_dict.get('tables', []))
    num_pictures = len(doc_dict.get('pictures', []))

    if num_texts == 0 and num_tables == 0:
        issues.append("No text or table content extracted")

    # Valid if no critical issues (extra pages outside range is critical)
    is_valid = not any('outside chunk range' in i or 'Processing failed' in i or 'No text or table' in i for i in issues)

    return {
        'chunk': chunk_name,
        'chunk_idx': chunk_idx,
        'original_pages': (start_page, end_page),
        'chunk_page_count': chunk_page_count,
        'provenance_pages': prov_pages,
        'coverage_pct': coverage,
        'num_texts': num_texts,
        'num_tables': num_tables,
        'num_pictures': num_pictures,
        'valid': is_valid,
        'issues': issues
    }


def validate_global_coverage(results: list[dict], chunk_validations: list[dict]) -> list[str]:
    """
    Validate that all pages across all chunks are covered.

    Note: Since provenance is relative to each chunk, we validate that
    each chunk has good internal coverage, not absolute page numbers.
    """
    issues = []

    # Check overall statistics
    total_chunks = len(chunk_validations)
    chunks_with_content = sum(1 for v in chunk_validations if v.get('num_texts', 0) > 0 or v.get('num_tables', 0) > 0)

    if chunks_with_content < total_chunks:
        issues.append(f"{total_chunks - chunks_with_content} chunks have no extracted content")

    # Check average coverage
    coverages = [v.get('coverage_pct', 0) for v in chunk_validations if 'coverage_pct' in v]
    if coverages:
        avg_coverage = sum(coverages) / len(coverages)
        if avg_coverage < 80:
            issues.append(f"Average page coverage is low: {avg_coverage:.1f}%")

    # Check for gaps in chunk sequence
    chunk_indices = sorted([v.get('chunk_idx', -1) for v in chunk_validations if v.get('chunk_idx') is not None])
    if chunk_indices:
        expected_indices = list(range(chunk_indices[0], chunk_indices[-1] + 1))
        missing_chunks = set(expected_indices) - set(chunk_indices)
        if missing_chunks:
            issues.append(f"Missing chunk indices: {sorted(missing_chunks)}")

    # Check page continuity across chunks
    all_ranges = []
    for v in chunk_validations:
        if 'original_pages' in v and v['original_pages'][0] is not None:
            all_ranges.append(v['original_pages'])

    all_ranges.sort(key=lambda x: x[0])

    # Check for gaps between chunks
    for i in range(1, len(all_ranges)):
        prev_end = all_ranges[i-1][1]
        curr_start = all_ranges[i][0]
        if curr_start > prev_end + 1:
            issues.append(f"Gap between chunks: pages {prev_end+1}-{curr_start-1} not covered")

    return issues


def main():
    # Parse arguments
    docling_json = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('as-docling.json')
    chunks_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('assets/output')

    print(f"Validating: {docling_json}")
    print(f"Against chunks in: {chunks_dir}")
    print("=" * 70)

    # Load docling output
    if not docling_json.exists():
        print(f"ERROR: {docling_json} not found")
        sys.exit(1)

    with open(docling_json) as f:
        results = json.load(f)

    print(f"Loaded {len(results)} chunk results\n")

    # Validate each chunk
    validations = []
    for result in results:
        v = validate_chunk(result, chunks_dir)
        validations.append(v)

    # Sort by chunk index
    validations.sort(key=lambda x: x.get('chunk_idx', 999))

    # Print per-chunk results
    print("Per-Chunk Validation:")
    print("-" * 70)

    valid_count = 0
    for v in validations:
        status = "OK" if v['valid'] else "FAIL"
        if v['valid']:
            valid_count += 1

        pages_str = ""
        if 'original_pages' in v and v['original_pages'][0] is not None:
            pages_str = f" (orig {v['original_pages'][0]}-{v['original_pages'][1]})"

        coverage_str = ""
        if 'coverage_pct' in v:
            coverage_str = f" {v['coverage_pct']:.0f}%"

        content_str = ""
        if 'num_texts' in v:
            content_str = f" [t:{v['num_texts']}, tbl:{v['num_tables']}, pic:{v['num_pictures']}]"

        print(f"[{status:4}] {v['chunk']}{pages_str}{coverage_str}{content_str}")

        for issue in v.get('issues', []):
            print(f"       - {issue}")

    print("-" * 70)
    print(f"Chunk validation: {valid_count}/{len(validations)} passed\n")

    # Global validation
    print("Global Validation:")
    print("-" * 70)

    global_issues = validate_global_coverage(results, validations)

    if global_issues:
        for issue in global_issues:
            print(f"- {issue}")
    else:
        print("- All pages covered across chunks")

    # Summary statistics
    total_texts = sum(v.get('num_texts', 0) for v in validations)
    total_tables = sum(v.get('num_tables', 0) for v in validations)
    total_pictures = sum(v.get('num_pictures', 0) for v in validations)

    print(f"\nTotal elements extracted:")
    print(f"  - Texts: {total_texts}")
    print(f"  - Tables: {total_tables}")
    print(f"  - Pictures: {total_pictures}")

    # Final result
    print("\n" + "=" * 70)
    all_valid = valid_count == len(validations) and len(global_issues) == 0
    if all_valid:
        print("VALIDATION PASSED")
    else:
        print("VALIDATION FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
