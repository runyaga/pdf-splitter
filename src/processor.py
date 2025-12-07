"""
Processor Module (The Orchestrator)

Manages parallel workers and enforces memory cleanup through strict
process isolation using maxtasksperchild=1.

CRITICAL: DocumentConverter MUST be instantiated inside the worker function,
not passed from the main thread. This ensures the C++ backend is initialized
in the correct process space.
"""

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import os


logger = logging.getLogger(__name__)


def _process_chunk(chunk_path: str) -> Dict[str, Any]:
    """
    Worker function to process a single PDF chunk.

    IMPORTANT: This function instantiates DocumentConverter inside the worker
    to ensure proper C++ backend initialization and memory isolation.

    Args:
        chunk_path: Path to the chunk PDF file

    Returns:
        Dict containing:
        - 'success': bool indicating if processing succeeded
        - 'chunk_path': original chunk path
        - 'document': serialized DoclingDocument (if success)
        - 'error': error message (if failed)
    """
    # Import inside worker to ensure proper process isolation
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
    from docling.backend.docling_parse_v2_backend import DoclingParseV2DocumentBackend

    try:
        # Create converter with optimized settings
        pipeline_opts = PdfPipelineOptions()
        pipeline_opts.do_ocr = False
        pipeline_opts.table_structure_options.mode = TableFormerMode.FAST
        pipeline_opts.generate_page_images = False
        pipeline_opts.generate_picture_images = False

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_opts,
                    backend=DoclingParseV2DocumentBackend
                )
            }
        )

        # Process the chunk
        result = converter.convert(chunk_path)
        doc = result.document

        # Serialize document for cross-process transfer
        doc_json = doc.export_to_dict()

        return {
            'success': True,
            'chunk_path': chunk_path,
            'document_dict': doc_json,
            'error': None
        }

    except Exception as e:
        return {
            'success': False,
            'chunk_path': chunk_path,
            'document_dict': None,
            'error': str(e)
        }


class BatchProcessor:
    """
    Orchestrates parallel PDF chunk processing with strict memory isolation.

    Uses ProcessPoolExecutor with maxtasksperchild=1 to force a hard reset
    of memory space after every chunk, preventing DoclingParseV2 memory leak.
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        maxtasksperchild: int = 1
    ):
        """
        Initialize the batch processor.

        Args:
            max_workers: Maximum parallel workers (defaults to CPU count)
            maxtasksperchild: Tasks per worker before restart (default 1 for memory isolation)
        """
        self.max_workers = max_workers or os.cpu_count()
        self.maxtasksperchild = maxtasksperchild

    def execute_parallel(
        self,
        chunk_paths: List[Path],
        ordered: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Process multiple PDF chunks in parallel.

        Args:
            chunk_paths: List of paths to PDF chunk files
            ordered: If True, results maintain input order

        Returns:
            List of result dicts from _process_chunk, in order if ordered=True
        """
        if not chunk_paths:
            return []

        chunk_str_paths = [str(p) for p in chunk_paths]
        results = [None] * len(chunk_paths)
        path_to_idx = {p: i for i, p in enumerate(chunk_str_paths)}

        logger.info(
            f"Starting parallel processing of {len(chunk_paths)} chunks "
            f"with {self.max_workers} workers (maxtasksperchild={self.maxtasksperchild})"
        )

        with ProcessPoolExecutor(
            max_workers=self.max_workers,
            max_tasks_per_child=self.maxtasksperchild
        ) as executor:
            # Submit all chunks
            future_to_path = {
                executor.submit(_process_chunk, path): path
                for path in chunk_str_paths
            }

            # Collect results as they complete
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                idx = path_to_idx[path]

                try:
                    result = future.result()
                    results[idx] = result

                    if result['success']:
                        logger.info(f"Processed chunk {idx + 1}/{len(chunk_paths)}: {path}")
                    else:
                        logger.error(f"Failed chunk {idx + 1}/{len(chunk_paths)}: {result['error']}")

                except Exception as e:
                    logger.error(f"Exception processing {path}: {e}")
                    results[idx] = {
                        'success': False,
                        'chunk_path': path,
                        'document_dict': None,
                        'error': str(e)
                    }

        return results if ordered else [r for r in results if r is not None]

    def execute_sequential(self, chunk_paths: List[Path]) -> List[Dict[str, Any]]:
        """
        Process chunks sequentially (useful for debugging or memory testing).

        Args:
            chunk_paths: List of paths to PDF chunk files

        Returns:
            List of result dicts from _process_chunk
        """
        results = []
        for i, chunk_path in enumerate(chunk_paths):
            logger.info(f"Processing chunk {i + 1}/{len(chunk_paths)}: {chunk_path}")
            result = _process_chunk(str(chunk_path))
            results.append(result)

            if not result['success']:
                logger.error(f"Failed: {result['error']}")

        return results
