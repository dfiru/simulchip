"""Batch processing utilities for Simulchip.

This module provides batch processing functionality for handling
multiple decklists and other batch operations.
"""

# Standard library imports
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class BatchResult:
    """Result of a batch operation."""

    success_count: int
    failed_count: int
    total_count: int
    results: List[Dict[str, Any]]

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_count == 0:
            return 0.0
        return (self.success_count / self.total_count) * 100


def read_urls_from_file(file_path: Path) -> List[str]:
    """Read URLs from a file, filtering out comments and empty lines.

    Args:
        file_path: Path to the file containing URLs

    Returns:
        List of URLs

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file contains no valid URLs
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    urls = []
    with open(file_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)

    if not urls:
        raise ValueError(f"No URLs found in {file_path}")

    return urls


def process_batch(
    items: List[Any],
    process_func: Callable[[Any], Any],
    progress_callback: Optional[Callable[[int, int, Any], None]] = None,
    error_callback: Optional[Callable[[Any, Exception], None]] = None,
) -> BatchResult:
    """Process a batch of items with a given function.

    Args:
        items: List of items to process
        process_func: Function to apply to each item
        progress_callback: Optional callback for progress updates (current, total, item)
        error_callback: Optional callback for handling errors (item, error)

    Returns:
        BatchResult with success/failure counts and results
    """
    results = []
    success_count = 0
    failed_count = 0

    for i, item in enumerate(items):
        try:
            if progress_callback:
                progress_callback(i + 1, len(items), item)

            result = process_func(item)
            results.append(
                {"item": item, "success": True, "result": result, "error": None}
            )
            success_count += 1

        except Exception as e:
            if error_callback:
                error_callback(item, e)

            results.append(
                {
                    "item": item,
                    "success": False,
                    "result": None,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            )
            failed_count += 1

    return BatchResult(
        success_count=success_count,
        failed_count=failed_count,
        total_count=len(items),
        results=results,
    )


def process_decklist_batch(
    decklist_file: Path,
    generate_func: Callable[[str], Any],
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    error_callback: Optional[Callable[[str, Exception], None]] = None,
) -> BatchResult:
    """Process a batch of decklists from a file.

    Args:
        decklist_file: Path to file containing decklist URLs
        generate_func: Function to generate proxy for each URL
        progress_callback: Optional callback for progress updates
        error_callback: Optional callback for handling errors

    Returns:
        BatchResult with processing statistics

    Raises:
        FileNotFoundError: If the decklist file doesn't exist
        ValueError: If the file contains no valid URLs
    """
    urls = read_urls_from_file(decklist_file)

    return process_batch(
        items=urls,
        process_func=generate_func,
        progress_callback=progress_callback,
        error_callback=error_callback,
    )


def format_batch_summary(result: BatchResult) -> str:
    """Format a batch result into a readable summary.

    Args:
        result: BatchResult to format

    Returns:
        Formatted summary string
    """
    lines = [
        "Batch complete!",
        f"Success: {result.success_count}",
        f"Failed: {result.failed_count}",
        f"Total: {result.total_count}",
        f"Success rate: {result.success_rate:.1f}%",
    ]

    return "\n".join(lines)
