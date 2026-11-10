#!/usr/bin/env python3
"""
Annual report generation integration module.

This module wires together the annual report components to provide
a complete annual report generation workflow.
"""

import logging
from pathlib import Path
from typing import Sequence

from sotd.report.report_core import run_report  # Import run_report from new module
from sotd.utils.data_dir import get_data_dir
from sotd.utils.file_io import save_json_data, save_text_data
from sotd.utils.performance import PerformanceMonitor

from . import cli
from .annual_generator import generate_annual_report  # noqa: F401

logger = logging.getLogger(__name__)


def run_annual_report(args) -> None:
    """Main annual report generation logic with performance monitoring."""
    monitor = PerformanceMonitor("annual_run")
    monitor.start_total_timing()

    # Initialize variables to avoid linter errors
    years: list[str] = []
    years_successful = 0
    years_failed = 0
    total_report_size_chars = 0

    try:
        if args.debug:
            logger.debug("Annual report phase started")
            logger.debug(f"Annual: {args.annual}")
            logger.debug(f"Year: {args.year}")
            logger.debug(f"Range: {args.range}")
            logger.debug(f"Report type: {args.type}")
            logger.debug(f"Output directory: {args.data_dir}")
            logger.debug(f"Output format: {getattr(args, 'format', 'markdown')}")
            logger.debug(f"Force overwrite: {args.force}")

        # Convert output directory to Path
        # For consistency with other phases, use data_dir for both input (aggregated data) and output (reports)
        out_dir = get_data_dir(args.data_dir)
        data_root = (
            out_dir  # Use data_dir for reading aggregated data, consistent with other phases
        )

        # Determine years to process
        if args.year:
            years = [args.year]
        elif args.range:
            # Parse year range for annual mode
            start_year, end_year = args.range.split(":")
            start_year_int, end_year_int = int(start_year), int(end_year)
            # Ensure start_year <= end_year for proper range generation
            actual_start = min(start_year_int, end_year_int)
            actual_end = max(start_year_int, end_year_int)
            years = [str(year) for year in range(actual_start, actual_end + 1)]
        else:
            raise ValueError("Annual reports require either --year or --range")

        # Determine which report types to generate
        if args.type == "all":
            report_types = ["hardware", "software"]
            logger.info(
                f"Generating annual reports for years {years} (both hardware and software)..."
            )
        else:
            report_types = [args.type]
            logger.info(f"Generating annual {args.type} reports for years {years}...")

        if args.debug:
            logger.debug(f"Processing years: {years}")
            logger.debug(f"Report types: {report_types}")

        # Process each year in the range
        for year in years:
            if args.debug:
                logger.debug(f"Generating annual reports for {year}")

            # Generate reports for each type
            for report_type in report_types:
                if args.debug:
                    logger.debug(f"Generating annual {report_type} report for {year}")

                output_format = getattr(args, "format", "markdown")

                # Create generator for both markdown and JSON generation
                from .annual_comparison_loader import AnnualComparisonLoader
                from .annual_generator import create_annual_report_generator
                from .annual_load import get_annual_file_path, load_annual_data

                # Load annual data
                annual_data_file = get_annual_file_path(data_root, year)
                if not annual_data_file.exists():
                    years_failed += 1
                    logger.error(
                        f"Annual data not found for {year}. "
                        f"Run the aggregate phase first with --annual --year {year} "
                        f"to generate the required data."
                    )
                    raise FileNotFoundError(
                        f"Annual data not found for {year}. "
                        f"Run the aggregate phase first with --annual --year {year} "
                        f"to generate the required data."
                    )

                metadata, data = load_annual_data(annual_data_file, debug=args.debug)

                # Load comparison data for delta calculations
                comparison_data = {}
                try:
                    loader = AnnualComparisonLoader(debug=args.debug)
                    annual_data_dir = data_root / "aggregated" / "annual"
                    year_int = int(year)
                    comparison_years = [str(year_int - 1), str(year_int - 5)]
                    comparison_years_data = loader.load_comparison_years(
                        comparison_years, annual_data_dir
                    )
                    for comp_year, comp_data in comparison_years_data.items():
                        comp_metadata = comp_data.get("metadata", {})
                        comp_data_section = {k: v for k, v in comp_data.items() if k != "metadata"}
                        comparison_data[f"{comp_year}-12"] = (comp_metadata, comp_data_section)
                except Exception as e:
                    if args.debug:
                        logger.debug(f"Warning: Failed to load comparison data: {e}")

                # Construct template path from data_root (templates are in data_root/report_templates)
                template_path = str(data_root / "report_templates")
                generator = create_annual_report_generator(
                    report_type,
                    year,
                    metadata,
                    data,
                    comparison_data,
                    args.debug,
                    template_path,
                    no_slug=getattr(args, "no_slug", False),
                )

                # Generate and save markdown if requested
                if output_format in ["markdown", "both"]:
                    try:
                        report_content = generator.generate_report()
                        total_report_size_chars += len(report_content)
                        logger.info(f"  {year} {report_type}: generated")
                    except Exception as e:
                        years_failed += 1
                        logger.error(
                            f"Failed to generate annual {report_type} markdown report: {e}"
                        )
                        raise RuntimeError(
                            f"Failed to generate annual {report_type} markdown report: {e}"
                        ) from e

                    try:
                        # Save markdown report to file
                        if args.debug:
                            logger.debug(f"Saving annual {report_type} markdown report for {year}")
                        monitor.start_file_io_timing()
                        output_path = save_annual_report(
                            report_content, out_dir, year, report_type, args.force, args.debug
                        )
                        monitor.end_file_io_timing()
                        logger.info(f"  {year} {report_type}: {output_path.name}")
                    except OSError:
                        monitor.end_file_io_timing()
                        years_failed += 1
                        logger.error(
                            f"Failed to save annual {report_type} markdown report for {year}"
                        )
                        raise
                    except Exception as e:
                        monitor.end_file_io_timing()
                        years_failed += 1
                        logger.error(f"Failed to save annual {report_type} markdown report: {e}")
                        raise RuntimeError(
                            f"Failed to save annual {report_type} markdown report: {e}"
                        ) from e

                # Generate and save JSON if requested
                if output_format in ["json", "both"]:
                    try:
                        structured_data = generator.get_structured_data()
                    except Exception as e:
                        years_failed += 1
                        logger.error(f"Failed to generate annual {report_type} JSON report: {e}")
                        raise RuntimeError(
                            f"Failed to generate annual {report_type} JSON report: {e}"
                        ) from e

                    try:
                        # Save JSON report to file
                        if args.debug:
                            logger.debug(f"Saving annual {report_type} JSON report for {year}")
                        monitor.start_file_io_timing()
                        output_path = save_annual_json_report(
                            structured_data, out_dir, year, report_type, args.force, args.debug
                        )
                        monitor.end_file_io_timing()
                        logger.info(f"  {year} {report_type}: {output_path.name}")
                    except OSError:
                        monitor.end_file_io_timing()
                        years_failed += 1
                        logger.error(f"Failed to save annual {report_type} JSON report for {year}")
                        raise
                    except Exception as e:
                        monitor.end_file_io_timing()
                        years_failed += 1
                        logger.error(f"Failed to save annual {report_type} JSON report: {e}")
                        raise RuntimeError(
                            f"Failed to save annual {report_type} JSON report: {e}"
                        ) from e

            years_successful += 1

        # Final success message
        if len(years) == 1:
            logger.info(f"Annual report generation completed for {years[0]}")
        else:
            logger.info(
                f"Annual report generation completed for {len(years)} years: {', '.join(years)}"
            )

        # Update final metrics
        monitor.metrics.record_count = years_successful

    finally:
        monitor.end_total_timing()
        if args.debug:
            logger.debug("\n=== Annual Run Performance Summary ===")
            logger.debug(f"Total Processing Time: {monitor.metrics.total_processing_time:.2f}s")
            logger.debug(f"File I/O Time: {monitor.metrics.file_io_time:.2f}s")
            logger.debug(f"Years Processed: {len(years)}")
            logger.debug(f"Years Successful: {years_successful}")
            logger.debug(f"Years Failed: {years_failed}")
            logger.debug(f"Report Type: {args.type}")
            logger.debug(f"Total Report Size: {total_report_size_chars:,} characters")
            logger.debug(f"Peak Memory Usage: {monitor.metrics.peak_memory_mb:.1f}MB")


def save_annual_report(
    report_content: str,
    out_dir: Path,
    year: str,
    report_type: str,
    force: bool = False,
    debug: bool = False,
) -> Path:
    """Save annual report content to file with unified file I/O patterns.

    Args:
        report_content: The report content to save
        out_dir: Output directory for the report file
        year: Year for the report (YYYY format)
        report_type: Type of report ('hardware' or 'software')
        force: Whether to force overwrite existing files
        debug: Enable debug logging

    Returns:
        Path to the saved report file

    Raises:
        FileExistsError: If file exists and force=False
        OSError: If there are file system errors
    """
    if debug:
        logger.debug(f"Saving annual {report_type} report for {year}")
        logger.debug(f"Output directory: {out_dir}")

    # Create annual reports subdirectory (consistent with annual aggregations)
    reports_dir = out_dir / "report" / "annual"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Generate output filename
    output_filename = f"{year}-{report_type}.md"
    output_path = reports_dir / output_filename

    if debug:
        logger.debug(f"Output file: {output_path}")

    # Check if file exists and handle force flag
    if output_path.exists() and not force:
        logger.error(f"Report file already exists: {output_path}")
        raise FileExistsError(f"Report file already exists: {output_path}")

    # Write report content to file using unified file I/O (atomic: temp
    # file + replace, so a failed write leaves any pre-existing report
    # intact instead of truncating it in place).
    try:
        save_text_data(report_content, output_path)
    except OSError as e:
        logger.error(f"Failed to write report file {output_path}: {e}")
        raise OSError(f"Failed to write report file {output_path}: {e}") from e

    if debug:
        logger.debug(f"Successfully saved report to: {output_path}")

    return output_path


def save_annual_json_report(
    data: dict,
    out_dir: Path,
    year: str,
    report_type: str,
    force: bool = False,
    debug: bool = False,
) -> Path:
    """Save annual structured report data to JSON file.

    Args:
        data: Structured report data (dict) to save
        out_dir: Output directory for the report file
        year: Year for the report (YYYY format)
        report_type: Type of report ('hardware' or 'software')
        force: Whether to force overwrite existing files
        debug: Enable debug logging

    Returns:
        Path to the saved JSON report file

    Raises:
        FileExistsError: If file exists and force=False
        OSError: If there are file system errors
    """
    if debug:
        logger.debug(f"Saving annual {report_type} JSON report for {year}")
        logger.debug(f"Output directory: {out_dir}")

    # Create annual reports subdirectory (consistent with annual aggregations)
    reports_dir = out_dir / "report" / "annual"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Generate output filename
    output_filename = f"{year}-{report_type}.json"
    output_path = reports_dir / output_filename

    if debug:
        logger.debug(f"Output file: {output_path}")

    # Check if file exists and handle force flag
    if output_path.exists() and not force:
        logger.error(f"JSON report file already exists: {output_path}")
        raise FileExistsError(f"JSON report file already exists: {output_path}")

    # Write JSON data to file using unified file I/O (atomic: temp file +
    # replace). Output format is unchanged: indent=2, ensure_ascii=False.
    try:
        save_json_data(data, output_path)
    except (OSError, TypeError) as e:
        logger.error(f"Failed to write JSON report file {output_path}: {e}")
        raise OSError(f"Failed to write JSON report file {output_path}: {e}") from e

    if debug:
        logger.debug(f"Successfully saved JSON report to: {output_path}")

    return output_path


def main(argv: Sequence[str] | None = None) -> None:
    """Main entry point for the annual report phase."""
    try:
        parser = cli.get_parser()
        args = parser.parse_args(argv)
        cli.validate_args(args)

        # Route to appropriate function based on annual flag
        if args.annual:
            run_annual_report(args)
        else:
            run_report(args)
    except KeyboardInterrupt:
        logger.info("Report generation interrupted by user")
    except Exception as e:
        logger.error(f"Report generation failed: {e}")


if __name__ == "__main__":
    main()
