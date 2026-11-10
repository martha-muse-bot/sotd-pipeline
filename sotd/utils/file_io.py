"""
Unified file I/O utilities for the SOTD Pipeline.

This module provides standardized file operations for JSON and YAML data,
with atomic writes, error handling, and consistent formatting.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


def save_json_data(data: Dict[str, Any], file_path: Path, indent: int = 2) -> None:
    """
    Save JSON data with atomic writes and proper formatting.

    Args:
        data: Dictionary data to save
        file_path: Path to save the file
        indent: JSON indentation level (default: 2)

    Raises:
        OSError: If file cannot be written
        TypeError: If data cannot be serialized to JSON
    """
    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create temporary file for atomic write
    temp_path = file_path.with_suffix(".tmp")

    try:
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)

        # Atomic move
        temp_path.replace(file_path)
        logger.debug(f"Saved JSON data to {file_path}")

    except (OSError, TypeError) as e:
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()
        raise e


def save_text_data(content: str, file_path: Path) -> None:
    """
    Save text data with atomic writes and proper formatting.

    Args:
        content: String content to save
        file_path: Path to save the file

    Raises:
        OSError: If file cannot be written
        TypeError: If content cannot be written as text
    """
    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create temporary file for atomic write
    temp_path = file_path.with_suffix(".tmp")

    try:
        with temp_path.open("w", encoding="utf-8") as f:
            f.write(content)

        # Atomic move
        temp_path.replace(file_path)
        logger.debug(f"Saved text data to {file_path}")

    except (OSError, TypeError) as e:
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()
        raise e


def load_json_data(file_path: Path) -> Dict[str, Any]:
    """
    Load JSON data with error handling.

    Args:
        file_path: Path to the JSON file

    Returns:
        Dictionary containing the loaded data

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
        OSError: If file cannot be read
    """
    if not file_path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        logger.debug(f"Loaded JSON data from {file_path}")
        return data

    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in {file_path}: {e.msg}", e.doc, e.pos)
    except PermissionError:
        raise
    except OSError as e:
        raise OSError(f"Error reading JSON file {file_path}: {e}")


def save_yaml_data(data: Dict[str, Any], file_path: Path, default_flow_style: bool = False) -> None:
    """
    Save YAML data with atomic writes and proper formatting.

    Args:
        data: Dictionary data to save
        file_path: Path to save the file
        default_flow_style: YAML flow style setting (default: False for block style)

    Raises:
        OSError: If file cannot be written
        yaml.YAMLError: If data cannot be serialized to YAML
    """
    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create temporary file for atomic write
    temp_path = file_path.with_suffix(".tmp")

    try:
        with temp_path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=default_flow_style, allow_unicode=True)

        # Atomic move
        temp_path.replace(file_path)
        logger.debug(f"Saved YAML data to {file_path}")

    except (OSError, yaml.YAMLError) as e:
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()
        raise e


def load_yaml_data(file_path: Path) -> Dict[str, Any]:
    """
    Load YAML data with error handling.

    Args:
        file_path: Path to the YAML file

    Returns:
        Dictionary containing the loaded data

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If file contains invalid YAML
        OSError: If file cannot be read
    """
    if not file_path.exists():
        raise FileNotFoundError(f"YAML file not found: {file_path}")

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        logger.debug(f"Loaded YAML data from {file_path}")
        return data or {}  # Return empty dict if file is empty

    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in {file_path}: {e}")
    except OSError as e:
        raise OSError(f"Error reading YAML file {file_path}: {e}")


def get_file_size_mb(file_path: Path) -> float:
    """
    Get file size in megabytes.

    Args:
        file_path: Path to the file

    Returns:
        File size in megabytes (0.0 if file doesn't exist)
    """
    if not file_path.exists():
        return 0.0

    size_bytes = file_path.stat().st_size
    return size_bytes / (1024 * 1024)


def ensure_directory_exists(directory_path: Path) -> None:
    """
    Ensure directory exists, creating it if necessary.

    Args:
        directory_path: Path to the directory
    """
    directory_path.mkdir(parents=True, exist_ok=True)


def backup_file(file_path: Path, backup_suffix: str = ".backup") -> Optional[Path]:
    """
    Create a backup of a file if it exists.

    Args:
        file_path: Path to the file to backup
        backup_suffix: Suffix for the backup file

    Returns:
        Path to the backup file, or None if original file doesn't exist
    """
    if not file_path.exists():
        return None

    backup_path = file_path.with_suffix(file_path.suffix + backup_suffix)

    try:
        # Use atomic copy
        import shutil

        shutil.copy2(file_path, backup_path)
        logger.debug(f"Created backup: {backup_path}")
        return backup_path

    except OSError as e:
        logger.warning(f"Failed to create backup of {file_path}: {e}")
        return None


__all__ = [
    "save_json_data",
    "save_text_data",
    "load_json_data",
    "save_yaml_data",
    "load_yaml_data",
    "get_file_size_mb",
    "ensure_directory_exists",
    "backup_file",
]
