"""
Reassembly Module

Stitches processed chunks back into a cohesive document using
DoclingDocument.concatenate() for native object-level merging.

This preserves:
- DOM tree structure
- Provenance data
- Page number offsetting
"""

from typing import List, Dict, Any, Optional
from docling_core.types.doc import DoclingDocument
import logging


logger = logging.getLogger(__name__)


def merge_documents(docs: List[DoclingDocument]) -> Optional[DoclingDocument]:
    """
    Merge multiple DoclingDocuments into a single cohesive document.

    Uses DoclingDocument.concatenate() which automatically handles:
    - Page number offsetting
    - DOM tree merging
    - Provenance data preservation

    Args:
        docs: List of DoclingDocument objects to merge

    Returns:
        Merged DoclingDocument, or None if input is empty
    """
    if not docs:
        logger.warning("No documents provided for merging")
        return None

    if len(docs) == 1:
        return docs[0]

    # Initialize with first document
    master_doc = docs[0]
    logger.info(f"Starting merge with document 1/{len(docs)}")

    # Concatenate remaining documents
    for i, doc in enumerate(docs[1:], start=2):
        try:
            master_doc = master_doc.concatenate(doc)
            logger.info(f"Merged document {i}/{len(docs)}")
        except Exception as e:
            logger.error(f"Failed to merge document {i}: {e}")
            raise

    return master_doc


def merge_from_results(results: List[Dict[str, Any]]) -> Optional[DoclingDocument]:
    """
    Reconstruct DoclingDocuments from processor results and merge them.

    Args:
        results: List of result dicts from BatchProcessor.execute_parallel()
                 Each dict should have 'document_dict' with serialized document

    Returns:
        Merged DoclingDocument, or None if no valid documents
    """
    docs = []

    for i, result in enumerate(results):
        if not result.get('success'):
            logger.warning(f"Skipping failed chunk {i}: {result.get('error')}")
            continue

        doc_dict = result.get('document_dict')
        if doc_dict is None:
            logger.warning(f"Chunk {i} has no document data")
            continue

        try:
            # Reconstruct DoclingDocument from serialized dict
            doc = DoclingDocument.model_validate(doc_dict)
            docs.append(doc)
        except Exception as e:
            logger.error(f"Failed to reconstruct document {i}: {e}")

    if not docs:
        logger.error("No valid documents to merge")
        return None

    logger.info(f"Merging {len(docs)} valid documents from {len(results)} results")
    return merge_documents(docs)


def validate_provenance_monotonicity(doc: DoclingDocument) -> bool:
    """
    Verify that page numbers in provenance data are monotonically increasing.

    This validates that concatenate() properly handled page number offsetting.

    Args:
        doc: The merged DoclingDocument to validate

    Returns:
        True if page numbers are monotonically increasing (or equal)
    """
    page_numbers = extract_provenance_pages(doc)

    if not page_numbers:
        return True

    for i in range(1, len(page_numbers)):
        if page_numbers[i] < page_numbers[i - 1]:
            logger.error(
                f"Provenance monotonicity violation: page {page_numbers[i]} "
                f"follows page {page_numbers[i-1]} at index {i}"
            )
            return False

    return True


def extract_provenance_pages(doc: DoclingDocument) -> List[int]:
    """
    Extract all page numbers from document provenance data.

    Args:
        doc: DoclingDocument to inspect

    Returns:
        List of page numbers in document order
    """
    page_numbers = []

    try:
        # Iterate through all content items with provenance
        for item, _level in doc.iterate_items():
            if hasattr(item, 'prov') and item.prov:
                for prov in item.prov:
                    if hasattr(prov, 'page_no') and prov.page_no is not None:
                        page_numbers.append(prov.page_no)
    except Exception as e:
        logger.warning(f"Error extracting provenance pages: {e}")

    return page_numbers


def get_merge_statistics(doc: DoclingDocument) -> Dict[str, Any]:
    """
    Get statistics about a merged document.

    Args:
        doc: DoclingDocument to analyze

    Returns:
        Dict with statistics about the document structure
    """
    stats = {
        'total_items': 0,
        'tables': 0,
        'text_items': 0,
        'figures': 0,
        'unique_pages': set(),
        'page_range': (None, None),
    }

    try:
        for item, _level in doc.iterate_items():
            stats['total_items'] += 1

            # Count item types
            item_type = type(item).__name__
            if 'Table' in item_type:
                stats['tables'] += 1
            elif 'Text' in item_type or 'Paragraph' in item_type:
                stats['text_items'] += 1
            elif 'Figure' in item_type or 'Picture' in item_type:
                stats['figures'] += 1

            # Track pages
            if hasattr(item, 'prov') and item.prov:
                for prov in item.prov:
                    if hasattr(prov, 'page_no') and prov.page_no is not None:
                        stats['unique_pages'].add(prov.page_no)

        # Calculate page range
        if stats['unique_pages']:
            stats['page_range'] = (
                min(stats['unique_pages']),
                max(stats['unique_pages'])
            )
            stats['unique_pages'] = len(stats['unique_pages'])
        else:
            stats['unique_pages'] = 0

    except Exception as e:
        logger.warning(f"Error calculating statistics: {e}")

    return stats
