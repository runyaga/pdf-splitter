"""
Segmentation Module

Splits monolith PDFs into logically safe chunks using:
1. Smart Splitting: Based on document hierarchy (bookmarks/outlines)
2. Fallback: Fixed-range splitting with overlap buffering for flat documents
"""

from pathlib import Path
from typing import List, Tuple
from pypdf import PdfReader, PdfWriter
import tempfile
import os


# Default chunk size for fallback splitting
DEFAULT_CHUNK_SIZE = 50
# Overlap buffer to prevent semantic fragmentation
DEFAULT_OVERLAP = 5


def get_split_boundaries(
    pdf_path: Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP
) -> List[Tuple[int, int]]:
    """
    Determine split boundaries for a PDF document.

    Uses bookmark-based splitting if outlines exist, otherwise falls back
    to fixed-range splitting with overlap buffering.

    Args:
        pdf_path: Path to the PDF file
        chunk_size: Number of pages per chunk (for fallback splitting)
        overlap: Number of overlapping pages between chunks (for fallback)

    Returns:
        List of tuples (start_page, end_page) representing chunk boundaries.
        Page numbers are 0-indexed.
    """
    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)

    if total_pages == 0:
        return []

    if total_pages == 1:
        return [(0, 1)]

    # Try smart splitting based on bookmarks
    boundaries = _get_bookmark_boundaries(reader, total_pages)

    if boundaries:
        return boundaries

    # Fallback to fixed-range splitting with overlap
    return _get_fixed_boundaries(total_pages, chunk_size, overlap)


def _get_bookmark_boundaries(
    reader: PdfReader,
    total_pages: int
) -> List[Tuple[int, int]]:
    """
    Extract split boundaries from PDF bookmarks/outlines.

    Args:
        reader: PdfReader instance
        total_pages: Total number of pages in the document

    Returns:
        List of (start, end) tuples based on top-level bookmarks,
        or empty list if no valid outlines found.
    """
    try:
        outline = reader.outline
        if not outline:
            return []

        # Extract page numbers from top-level bookmark items
        page_numbers = []
        for item in outline:
            # Skip nested lists (sub-bookmarks)
            if isinstance(item, list):
                continue

            try:
                page_num = reader.get_destination_page_number(item)
                if page_num is not None and 0 <= page_num < total_pages:
                    page_numbers.append(page_num)
            except (KeyError, AttributeError):
                # Skip invalid bookmark entries
                continue

        if not page_numbers:
            return []

        # Sort and deduplicate
        page_numbers = sorted(set(page_numbers))

        # Ensure we start from page 0
        if page_numbers[0] != 0:
            page_numbers.insert(0, 0)

        # Build boundaries
        boundaries = []
        for i in range(len(page_numbers)):
            start = page_numbers[i]
            end = page_numbers[i + 1] if i + 1 < len(page_numbers) else total_pages
            if start < end:
                boundaries.append((start, end))

        return boundaries

    except Exception:
        # Any error in outline processing falls back to fixed splitting
        return []


def _get_fixed_boundaries(
    total_pages: int,
    chunk_size: int,
    overlap: int
) -> List[Tuple[int, int]]:
    """
    Generate fixed-size chunk boundaries with overlap buffering.

    Args:
        total_pages: Total number of pages
        chunk_size: Pages per chunk
        overlap: Overlapping pages between chunks

    Returns:
        List of (start, end) tuples with overlap buffering
    """
    boundaries = []
    start = 0

    while start < total_pages:
        end = min(start + chunk_size, total_pages)
        boundaries.append((start, end))

        # Move start back by overlap for next chunk
        start = end - overlap if end < total_pages else total_pages

        # Prevent infinite loop if overlap >= chunk_size
        if start <= boundaries[-1][0]:
            break

    return boundaries


def split_pdf(
    pdf_path: Path,
    output_dir: Path = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP
) -> List[Path]:
    """
    Split a PDF into chunks and write them to disk.

    Args:
        pdf_path: Path to the source PDF
        output_dir: Directory to write chunks (uses temp dir if None)
        chunk_size: Pages per chunk for fallback splitting
        overlap: Overlap pages between chunks

    Returns:
        List of paths to the chunk PDF files
    """
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="pdf_chunks_"))
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(pdf_path))
    boundaries = get_split_boundaries(pdf_path, chunk_size, overlap)
    chunk_paths = []

    for idx, (start, end) in enumerate(boundaries):
        writer = PdfWriter()

        for page_num in range(start, end):
            writer.add_page(reader.pages[page_num])

        chunk_filename = f"chunk_{idx:04d}_pages_{start:04d}_{end:04d}.pdf"
        chunk_path = output_dir / chunk_filename

        with open(chunk_path, "wb") as f:
            writer.write(f)

        chunk_paths.append(chunk_path)

    return chunk_paths


def get_page_coverage(boundaries: List[Tuple[int, int]], total_pages: int) -> bool:
    """
    Verify that boundaries cover all pages without gaps.

    Args:
        boundaries: List of (start, end) tuples
        total_pages: Expected total pages

    Returns:
        True if all pages from 0 to total_pages-1 are covered
    """
    if not boundaries:
        return total_pages == 0

    covered = set()
    for start, end in boundaries:
        for page in range(start, end):
            covered.add(page)

    expected = set(range(total_pages))
    return covered == expected
