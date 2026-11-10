#!/usr/bin/env python3
"""File output functionality for the report phase."""

from pathlib import Path

from sotd.utils.file_io import save_json_data, save_text_data


def get_report_file_path(base_dir: Path, year: int, month: int, report_type: str) -> Path:
    """Get the path for the output report file.

    Args:
        base_dir: Base output directory
        year: Year of the report
        month: Month of the report
        report_type: Type of report ('hardware' or 'software')

    Returns:
        Path to the output report file
    """
    filename = f"{year:04d}-{month:02d}-{report_type}.md"
    return base_dir / "report" / filename


def save_report(
    content: str,
    output_path: Path,
    force: bool = False,
    debug: bool = False,
) -> None:
    """Save report content to a markdown file.

    Args:
        content: Report content to save
        output_path: Path where to save the file
        force: Whether to force overwrite existing files
        debug: Enable debug logging

    Raises:
        OSError: If there are file system errors
    """
    if debug:
        print(f"[DEBUG] Saving report to: {output_path}")

    # Atomic write (temp file + replace): a failed write leaves any
    # pre-existing report intact instead of truncating it in place.
    # The force flag needs no unlink here — replace overwrites atomically —
    # and skip-if-exists is enforced by the caller (report_core).
    try:
        save_text_data(content, output_path)
    except OSError as e:
        raise OSError(f"Failed to write report file {output_path}: {e}") from e

    if debug:
        print(f"[DEBUG] Successfully saved report to: {output_path}")


def get_json_report_file_path(base_dir: Path, year: int, month: int, report_type: str) -> Path:
    """Get the path for the output JSON report file.

    Args:
        base_dir: Base output directory
        year: Year of the report
        month: Month of the report
        report_type: Type of report ('hardware' or 'software')

    Returns:
        Path to the output JSON report file
    """
    filename = f"{year:04d}-{month:02d}-{report_type}.json"
    return base_dir / "report" / filename


def save_json_report(
    data: dict,
    output_path: Path,
    force: bool = False,
    debug: bool = False,
) -> None:
    """Save structured report data to a JSON file.

    Args:
        data: Structured report data (dict) to save
        output_path: Path where to save the file
        force: Whether to force overwrite existing files
        debug: Enable debug logging

    Raises:
        OSError: If there are file system errors
    """
    if debug:
        print(f"[DEBUG] Saving JSON report to: {output_path}")

    # Atomic write (temp file + replace); see save_report. Output format
    # is unchanged: indent=2, ensure_ascii=False, same as before.
    try:
        save_json_data(data, output_path)
    except (OSError, TypeError) as e:
        raise OSError(f"Failed to write JSON report file {output_path}: {e}") from e

    if debug:
        print(f"[DEBUG] Successfully saved JSON report to: {output_path}")


def generate_and_save_report(
    content: str,
    base_dir: Path,
    year: int,
    month: int,
    report_type: str,
    force: bool = False,
    debug: bool = False,
) -> Path:
    """Generate report file path and save content.

    Args:
        content: Report content to save
        base_dir: Base output directory
        year: Year of the report
        month: Month of the report
        report_type: Type of report ('hardware' or 'software')
        force: Whether to force overwrite existing files
        debug: Enable debug logging

    Returns:
        Path to the saved report file

    Raises:
        FileExistsError: If file exists and force=False
        OSError: If there are file system errors
    """
    output_path = get_report_file_path(base_dir, year, month, report_type)
    save_report(content, output_path, force, debug)
    return output_path


def generate_and_save_json_report(
    data: dict,
    base_dir: Path,
    year: int,
    month: int,
    report_type: str,
    force: bool = False,
    debug: bool = False,
) -> Path:
    """Generate JSON report file path and save structured data.

    Args:
        data: Structured report data (dict) to save
        base_dir: Base output directory
        year: Year of the report
        month: Month of the report
        report_type: Type of report ('hardware' or 'software')
        force: Whether to force overwrite existing files
        debug: Enable debug logging

    Returns:
        Path to the saved JSON report file

    Raises:
        FileExistsError: If file exists and force=False
        OSError: If there are file system errors
    """
    output_path = get_json_report_file_path(base_dir, year, month, report_type)
    save_json_report(data, output_path, force, debug)
    return output_path
