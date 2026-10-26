#!/usr/bin/env python3
"""Override manager for extract phase field corrections."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class OverrideManager:
    """Manages loading and application of field overrides for extract phase."""

    # Valid field names that can be overridden
    VALID_FIELDS = {"razor", "blade", "brush", "soap"}
    # Reserved month-level key for many-IDs → one field value (not a comment id)
    BULK_KEY = "bulk"

    def __init__(self, override_file_path: Path):
        """Initialize OverrideManager with path to override file.

        Args:
            override_file_path: Path to the YAML override file
        """
        self.override_file_path = override_file_path
        self.overrides: Dict[str, Dict[str, Dict[str, str]]] = {}
        self._file_lines: Optional[List[str]] = None

    def _find_field_line_number(self, month: str, comment_id: str, field: str) -> Optional[int]:
        """Find the line number where a field appears in the YAML file.

        Args:
            month: Month in YYYY-MM format
            comment_id: Reddit comment ID
            field: Field name to find

        Returns:
            Line number (1-indexed) or None if not found
        """
        if self._file_lines is None:
            try:
                with self.override_file_path.open("r", encoding="utf-8") as f:
                    self._file_lines = f.readlines()
            except (OSError, IOError):
                return None

        # Search for the field in the context of the month and comment_id
        in_target_month = False
        in_target_comment = False
        indent_level = 0

        for line_num, line in enumerate(self._file_lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Check if we're in the target month
            if stripped.startswith(month + ":"):
                in_target_month = True
                in_target_comment = False
                indent_level = len(line) - len(line.lstrip())
                continue

            # Check if we've moved to a different month
            if in_target_month and not line.strip().startswith(" ") and stripped.endswith(":"):
                if not stripped.startswith(month):
                    break

            if not in_target_month:
                continue

            # Check if we're in the target comment
            current_indent = len(line) - len(line.lstrip())
            if current_indent > indent_level and stripped.startswith(comment_id + ":"):
                in_target_comment = True
                comment_indent = current_indent
                continue

            # Check if we've moved to a different comment
            if in_target_comment:
                if current_indent <= indent_level:
                    in_target_comment = False
                    continue
                if current_indent == comment_indent and stripped.endswith(":"):
                    in_target_comment = False
                    continue

            # Check if this line contains the field
            if in_target_comment and stripped.startswith(field + ":"):
                return line_num

        return None

    def load_overrides(self) -> None:
        """Load overrides from YAML file with validation.

        Raises:
            ValueError: If override file has validation errors
            FileNotFoundError: If override file doesn't exist
            yaml.YAMLError: If YAML syntax is invalid
        """
        if not self.override_file_path.exists():
            # Override file is optional - pipeline continues normally
            logger.debug("Override file not found: %s", self.override_file_path)
            return

        try:
            with self.override_file_path.open("r", encoding="utf-8") as f:
                self._file_lines = f.readlines()
                # Reset file pointer and load YAML
                f.seek(0)
                content = yaml.safe_load(f)
        except yaml.YAMLError as e:
            # Try to extract line number from YAML error if available
            error_msg = f"Invalid YAML syntax in {self.override_file_path}"
            if hasattr(e, "problem_mark") and e.problem_mark:
                line_num = e.problem_mark.line + 1  # YAML line numbers are 0-indexed
                error_msg += f" at line {line_num}"
            error_msg += f": {e}"
            raise ValueError(error_msg)

        if content is None:
            # Empty file is valid
            logger.debug("Override file is empty: %s", self.override_file_path)
            return

        if not isinstance(content, dict):
            raise ValueError("Override file must contain a dictionary at root level")

        # Validate and load overrides (per-ID + optional month-level bulk)
        total_override_count = 0
        for month, month_data in content.items():
            if not isinstance(month_data, dict):
                raise ValueError(f"Month '{month}' must contain a dictionary of comment overrides")

            bulk_map = self._parse_bulk_overrides(month, month_data.get(self.BULK_KEY))
            per_id_map: Dict[str, Dict[str, str]] = {}

            for comment_id, field_data in month_data.items():
                if comment_id == self.BULK_KEY:
                    continue

                if not isinstance(field_data, dict):
                    raise ValueError(
                        f"Comment '{comment_id}' in month '{month}' must contain field overrides"
                    )

                comment_overrides: Dict[str, str] = {}
                for field, value in field_data.items():
                    stripped = self._validate_field_override_value(month, comment_id, field, value)
                    comment_overrides[field] = stripped

                if comment_overrides:
                    per_id_map[comment_id] = comment_overrides

            self._raise_on_override_conflicts(month, per_id_map, bulk_map)

            month_overrides: Dict[str, Dict[str, str]] = {}
            for comment_id, fields in bulk_map.items():
                month_overrides[comment_id] = dict(fields)
            for comment_id, fields in per_id_map.items():
                if comment_id not in month_overrides:
                    month_overrides[comment_id] = dict(fields)
                else:
                    month_overrides[comment_id].update(fields)

            if month_overrides:
                self.overrides[month] = month_overrides
                total_override_count += sum(len(fields) for fields in month_overrides.values())

        logger.debug("Loaded %d overrides from %s", total_override_count, self.override_file_path)

    def _validate_field_override_value(
        self, month: str, comment_id: str, field: str, value: Any
    ) -> str:
        """Validate a single field override value; return stripped string."""
        if field not in self.VALID_FIELDS:
            line_num = self._find_field_line_number(month, comment_id, field)
            error_msg = (
                f"Invalid field '{field}' in comment '{comment_id}' month '{month}' "
                f"in {self.override_file_path}"
            )
            if line_num:
                error_msg += f" (line {line_num})"
            error_msg += (
                f".\n  Field value: {repr(value) if isinstance(value, str) else value}\n"
                f"  Valid fields: {', '.join(sorted(self.VALID_FIELDS))}\n"
                f"  Hint: Did you mean 'soap' instead of '{field}'?"
            )
            raise ValueError(error_msg)

        if not isinstance(value, str):
            line_num = self._find_field_line_number(month, comment_id, field)
            error_msg = (
                f"Override value for field '{field}' in comment "
                f"'{comment_id}' month '{month}' in {self.override_file_path}"
            )
            if line_num:
                error_msg += f" (line {line_num})"
            error_msg += f" must be a string, got: {type(value).__name__} (value: {repr(value)})"
            raise ValueError(error_msg)

        if not value.strip():
            line_num = self._find_field_line_number(month, comment_id, field)
            error_msg = (
                f"Override value for field '{field}' in comment "
                f"'{comment_id}' month '{month}' in {self.override_file_path}"
            )
            if line_num:
                error_msg += f" (line {line_num})"
            error_msg += " cannot be empty or whitespace-only"
            raise ValueError(error_msg)

        if len(value.strip()) > 200:
            line_num = self._find_field_line_number(month, comment_id, field)
            error_msg = (
                f"Override value for field '{field}' in comment "
                f"'{comment_id}' month '{month}' in {self.override_file_path}"
            )
            if line_num:
                error_msg += f" (line {line_num})"
            error_msg += (
                f" is too long ({len(value.strip())} characters). Maximum length: 200 characters"
            )
            raise ValueError(error_msg)

        return value.strip()

    def _parse_bulk_overrides(self, month: str, bulk_data: Any) -> Dict[str, Dict[str, str]]:
        """Parse month-level bulk overrides into comment_id → field → value.

        Raises ValueError on invalid shape or duplicate comment+field within bulk.
        """
        if bulk_data is None:
            return {}

        if not isinstance(bulk_data, list):
            raise ValueError(
                f"Month '{month}' key '{self.BULK_KEY}' must be a list of bulk override entries "
                f"in {self.override_file_path}"
            )

        bulk_map: Dict[str, Dict[str, str]] = {}
        for index, entry in enumerate(bulk_data):
            if not isinstance(entry, dict):
                raise ValueError(
                    f"Bulk entry {index} in month '{month}' must be a dictionary "
                    f"in {self.override_file_path}"
                )

            missing = [k for k in ("field", "value", "comment_ids") if k not in entry]
            if missing:
                raise ValueError(
                    f"Bulk entry {index} in month '{month}' missing required key(s): "
                    f"{', '.join(missing)} in {self.override_file_path}"
                )

            field = entry["field"]
            value = entry["value"]
            comment_ids = entry["comment_ids"]

            if not isinstance(field, str) or field not in self.VALID_FIELDS:
                raise ValueError(
                    f"Invalid field '{field}' in bulk entry {index} month '{month}' "
                    f"in {self.override_file_path}. "
                    f"Valid fields: {', '.join(sorted(self.VALID_FIELDS))}"
                )

            if not isinstance(value, str):
                raise ValueError(
                    f"Bulk entry {index} in month '{month}' value must be a string, "
                    f"got: {type(value).__name__} in {self.override_file_path}"
                )
            stripped_value = value.strip()
            if not stripped_value:
                raise ValueError(
                    f"Bulk entry {index} in month '{month}' value cannot be empty "
                    f"or whitespace-only in {self.override_file_path}"
                )
            if len(stripped_value) > 200:
                raise ValueError(
                    f"Bulk entry {index} in month '{month}' value is too long "
                    f"({len(stripped_value)} characters). Maximum length: 200 characters "
                    f"in {self.override_file_path}"
                )

            if not isinstance(comment_ids, list) or not comment_ids:
                raise ValueError(
                    f"Bulk entry {index} in month '{month}' comment_ids must be a "
                    f"non-empty list in {self.override_file_path}"
                )

            for comment_id in comment_ids:
                if not isinstance(comment_id, str) or not comment_id.strip():
                    raise ValueError(
                        f"Bulk entry {index} in month '{month}' has invalid comment_id "
                        f"{repr(comment_id)} in {self.override_file_path}"
                    )
                cid = comment_id.strip()
                existing = bulk_map.get(cid, {}).get(field)
                if existing is not None:
                    raise ValueError(
                        f"Conflict for comment '{cid}' field '{field}' in month '{month}': "
                        f"appears in multiple bulk entries "
                        f"({repr(existing)} vs {repr(stripped_value)}) "
                        f"in {self.override_file_path}"
                    )
                bulk_map.setdefault(cid, {})[field] = stripped_value

        return bulk_map

    def _raise_on_override_conflicts(
        self,
        month: str,
        per_id_map: Dict[str, Dict[str, str]],
        bulk_map: Dict[str, Dict[str, str]],
    ) -> None:
        """Fail loudly when the same comment+field is set in both per-ID and bulk."""
        for comment_id, bulk_fields in bulk_map.items():
            per_id_fields = per_id_map.get(comment_id, {})
            for field, bulk_value in bulk_fields.items():
                if field in per_id_fields:
                    raise ValueError(
                        f"Conflict for comment '{comment_id}' field '{field}' in month "
                        f"'{month}': set in both per-ID override "
                        f"({repr(per_id_fields[field])}) and bulk "
                        f"({repr(bulk_value)}) in {self.override_file_path}"
                    )

    def get_override(self, month: str, comment_id: str, field: str) -> Optional[str]:
        """Get override value for specific field if it exists.

        Args:
            month: Month in YYYY-MM format
            comment_id: Reddit comment ID
            field: Field name to check for override

        Returns:
            Override value if exists, None otherwise
        """
        month_overrides = self.overrides.get(month, {})
        comment_overrides = month_overrides.get(comment_id, {})
        return comment_overrides.get(field)

    def validate_overrides(self, data: List[Dict[str, Any]]) -> None:
        """Validate that all override comment IDs exist in the data.

        Args:
            data: List of comment records to validate against

        Raises:
            ValueError: If any override references non-existent comment IDs
        """
        # Build set of existing comment IDs
        existing_ids = {record["id"] for record in data if "id" in record}

        # Check all override comment IDs exist
        missing_ids = []
        for month, month_overrides in self.overrides.items():
            for comment_id in month_overrides.keys():
                if comment_id not in existing_ids:
                    missing_ids.append(f"{month}:{comment_id}")

        if missing_ids:
            raise ValueError(
                f"Override file references non-existent comment IDs: {', '.join(missing_ids)}. "
                f"This usually means the override file is for a different "
                f"dataset or the data has changed."
            )

    def apply_override(
        self, field_data: Optional[Dict[str, str]], override_value: str, field_exists: bool
    ) -> Dict[str, str]:
        """Apply override to field data, creating or modifying as needed.

        Args:
            field_data: Existing field data dict or None if field doesn't exist
            override_value: Value to use for override
            field_exists: Whether the field existed in original data

        Returns:
            Modified or created field data dict
        """
        if field_exists and field_data is not None:
            # Override existing field
            result = field_data.copy()
            result["normalized"] = override_value
            result["overridden"] = "Normalized"
            logger.debug(
                "Applied override to existing field: %s -> %s",
                field_data.get("normalized"),
                override_value,
            )
            return result
        else:
            # Create new field
            logger.debug("Created new field from override: %s", override_value)
            return {
                "original": override_value,
                "normalized": override_value,
                "overridden": "Original,Normalized",
            }

    def has_overrides(self) -> bool:
        """Check if any overrides are loaded.

        Returns:
            True if overrides exist, False otherwise
        """
        return bool(self.overrides)

    def get_comment_overrides(self, month: str, comment_id: str) -> Dict[str, str]:
        """Return field overrides for a comment (empty dict if none)."""
        return dict(self.overrides.get(month, {}).get(comment_id, {}))

    def _validate_override_value(self, field: str, value: str) -> str:
        """Validate and normalize a single override value."""
        if field not in self.VALID_FIELDS:
            raise ValueError(
                f"Invalid field '{field}'. Valid fields: {', '.join(sorted(self.VALID_FIELDS))}"
            )
        if not isinstance(value, str):
            raise ValueError(
                f"Override value for field '{field}' must be a string, got: {type(value).__name__}"
            )
        stripped = value.strip()
        if not stripped:
            raise ValueError(
                f"Override value for field '{field}' cannot be empty or whitespace-only"
            )
        if len(stripped) > 200:
            raise ValueError(
                f"Override value for field '{field}' is too long ({len(stripped)} characters). "
                f"Maximum length: 200 characters"
            )
        return stripped

    def _write_overrides_file(self) -> None:
        """Atomically write current overrides to the YAML file."""
        from sotd.utils.file_io import save_yaml_data

        # Sort months and comment IDs for stable, readable output
        ordered: Dict[str, Dict[str, Dict[str, str]]] = {}
        for month in sorted(self.overrides.keys()):
            month_data = self.overrides[month]
            ordered[month] = {
                comment_id: dict(fields) for comment_id, fields in sorted(month_data.items())
            }
        save_yaml_data(ordered, self.override_file_path)
        self._file_lines = None

    def update_comment_overrides(
        self, month: str, comment_id: str, fields: Dict[str, Optional[str]]
    ) -> Dict[str, str]:
        """Upsert/delete field overrides for a comment and persist to YAML.

        Args:
            month: Month in YYYY-MM format
            comment_id: Reddit comment ID
            fields: Map of field name to value. A string upserts; None or "" deletes that field.
                Only razor/blade/brush/soap keys are accepted.

        Returns:
            Resulting field map for the comment after update (empty if all cleared).
        """
        if not month or len(month) != 7 or month[4] != "-":
            raise ValueError(f"Invalid month format: {month}. Expected YYYY-MM")
        if not comment_id or not str(comment_id).strip():
            raise ValueError("comment_id is required")

        # Reload from disk so we don't clobber concurrent edits
        self.load_overrides()

        comment_overrides = dict(self.overrides.get(month, {}).get(comment_id, {}))

        for field, value in fields.items():
            if field not in self.VALID_FIELDS:
                raise ValueError(
                    f"Invalid field '{field}'. Valid fields: {', '.join(sorted(self.VALID_FIELDS))}"
                )
            if value is None or (isinstance(value, str) and not value.strip()):
                comment_overrides.pop(field, None)
            else:
                comment_overrides[field] = self._validate_override_value(field, value)

        if month not in self.overrides:
            self.overrides[month] = {}

        if comment_overrides:
            self.overrides[month][comment_id] = comment_overrides
        else:
            self.overrides[month].pop(comment_id, None)
            if not self.overrides[month]:
                del self.overrides[month]

        self._write_overrides_file()
        return dict(comment_overrides)

    def get_override_summary(self) -> Dict[str, Any]:
        """Get summary statistics about loaded overrides.

        Returns:
            Dictionary with override statistics
        """
        total_overrides = 0
        month_counts = {}
        field_counts = {}

        for month, month_overrides in self.overrides.items():
            month_count = 0
            for comment_id, field_data in month_overrides.items():
                month_count += len(field_data)
                total_overrides += len(field_data)

                for field in field_data:
                    field_counts[field] = field_counts.get(field, 0) + 1

            month_counts[month] = month_count

        return {
            "total_overrides": total_overrides,
            "months_with_overrides": len(month_counts),
            "month_counts": month_counts,
            "field_counts": field_counts,
        }
