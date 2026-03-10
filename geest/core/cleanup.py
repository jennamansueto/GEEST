# -*- coding: utf-8 -*-
"""Cleanup utility for removing intermediate files generated during processing.

This module provides functionality to remove intermediate files from workflow
directories after processing is complete. When developer mode is disabled,
intermediate files (shapefiles, geopackages, etc.) are removed to reclaim
disk space, keeping only the essential output files (VRT, QML, TIF, error logs).

Addresses: https://github.com/worldbank/GEEST/issues/55
"""

import os
import traceback

from qgis.core import Qgis

from geest.utilities import log_message


# File extensions that should be preserved after cleanup.
# These are the final output files needed for the analysis results.
KEEP_EXTENSIONS = frozenset(
    {
        ".vrt",
        ".qml",
        ".tif",
    }
)

# Filenames (not extensions) that should always be preserved.
KEEP_FILENAMES = frozenset(
    {
        "error.txt",
    }
)


def clean_intermediate_files(
    directory: str,
    keep_extensions: frozenset = KEEP_EXTENSIONS,
    keep_filenames: frozenset = KEEP_FILENAMES,
) -> dict:
    """Remove intermediate files from a workflow directory.

    Recursively scans the given directory and removes all files that are not
    in the set of kept extensions or filenames. Empty subdirectories are also
    removed after file cleanup.

    This is intended to be called after the final VRT has been created and
    all processing is complete for a workflow.

    Args:
        directory: Absolute path to the workflow directory to clean.
        keep_extensions: Set of file extensions (including the dot) to preserve.
        keep_filenames: Set of exact filenames to preserve.

    Returns:
        A dict with summary statistics:
            - ``removed_count``: number of files removed
            - ``removed_bytes``: total bytes freed
            - ``kept_count``: number of files kept
            - ``errors``: list of ``(path, error_message)`` tuples for failures
    """
    if not os.path.isdir(directory):
        log_message(
            f"Cleanup skipped: directory does not exist: {directory}",
            tag="Geest",
            level=Qgis.Warning,
        )
        return {"removed_count": 0, "removed_bytes": 0, "kept_count": 0, "errors": []}

    removed_count = 0
    removed_bytes = 0
    kept_count = 0
    errors = []

    # Walk bottom-up so we can remove empty directories after deleting files
    for dirpath, dirnames, filenames in os.walk(directory, topdown=False):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            _, ext = os.path.splitext(filename)

            if ext.lower() in keep_extensions or filename in keep_filenames:
                kept_count += 1
                continue

            try:
                file_size = os.path.getsize(file_path)
                os.remove(file_path)
                removed_count += 1
                removed_bytes += file_size
                log_message(
                    f"Cleanup: removed {file_path}",
                    tag="Geest",
                    level=Qgis.Info,
                )
            except Exception as e:
                log_message(
                    f"Cleanup: failed to remove {file_path}: {e}",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                log_message(
                    traceback.format_exc(),
                    tag="Geest",
                    level=Qgis.Warning,
                )
                errors.append((file_path, str(e)))

        # Remove empty subdirectories (but never the root workflow directory)
        if dirpath != directory:
            try:
                if not os.listdir(dirpath):
                    os.rmdir(dirpath)
                    log_message(
                        f"Cleanup: removed empty directory {dirpath}",
                        tag="Geest",
                        level=Qgis.Info,
                    )
            except Exception as e:
                log_message(
                    f"Cleanup: failed to remove directory {dirpath}: {e}",
                    tag="Geest",
                    level=Qgis.Warning,
                )
                errors.append((dirpath, str(e)))

    _log_cleanup_summary(directory, removed_count, removed_bytes, kept_count, errors)

    return {
        "removed_count": removed_count,
        "removed_bytes": removed_bytes,
        "kept_count": kept_count,
        "errors": errors,
    }


def _log_cleanup_summary(
    directory: str,
    removed_count: int,
    removed_bytes: int,
    kept_count: int,
    errors: list,
) -> None:
    """Log a human-readable summary of the cleanup operation.

    Args:
        directory: The directory that was cleaned.
        removed_count: Number of files removed.
        removed_bytes: Total bytes freed.
        kept_count: Number of files kept.
        errors: List of error tuples.
    """
    freed_mb = removed_bytes / (1024 * 1024)
    summary = (
        f"Cleanup summary for {directory}: "
        f"removed {removed_count} files ({freed_mb:.1f} MB freed), "
        f"kept {kept_count} files"
    )
    if errors:
        summary += f", {len(errors)} errors"
    log_message(summary, tag="Geest", level=Qgis.Info)
