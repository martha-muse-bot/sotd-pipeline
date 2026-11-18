"""
Unit tests for logging configuration.
"""

import logging
import os
import time
from unittest.mock import patch

from sotd.utils.logging_config import (
    cleanup_old_logs,
    get_logger,
    setup_pipeline_logging,
    should_disable_tqdm,
)


class TestSetupPipelineLogging:
    """Test logging setup functionality."""

    def test_setup_logging_terminal_mode(self):
        """Test logging setup in terminal mode (no LOG_DIR)."""
        # Clear any existing handlers
        logging.getLogger().handlers.clear()

        # Remove LOG_DIR if set
        with patch.dict(os.environ, {}, clear=True):
            logger = setup_pipeline_logging(log_file=None, level=logging.INFO)

            # Should have StreamHandler
            handlers = logger.handlers
            assert len(handlers) == 1
            assert isinstance(handlers[0], logging.StreamHandler)

            # Check format includes level indicator
            formatter = handlers[0].formatter
            assert "[%(levelname)s]" in formatter._fmt

    def test_setup_logging_docker_mode(self, tmp_path):
        """Test logging setup in Docker mode (LOG_DIR set)."""
        # Clear any existing handlers
        logging.getLogger().handlers.clear()

        log_file = tmp_path / "pipeline.log"

        with patch.dict(os.environ, {"LOG_DIR": str(tmp_path)}, clear=False):
            logger = setup_pipeline_logging(log_file=log_file, level=logging.INFO)

            # Should have TimedRotatingFileHandler
            handlers = logger.handlers
            assert len(handlers) == 1
            from logging.handlers import TimedRotatingFileHandler

            assert isinstance(handlers[0], TimedRotatingFileHandler)

            # Check format includes level indicator
            formatter = handlers[0].formatter
            assert "[%(levelname)s]" in formatter._fmt

            # Check rotation settings
            handler = handlers[0]
            assert handler.when == "W0"  # Weekly on Monday
            assert handler.backupCount == 13  # ~90 days

    def test_setup_logging_with_log_level_env_var(self, tmp_path):
        """Test that LOG_LEVEL environment variable is respected."""
        # Clear any existing handlers
        logging.getLogger().handlers.clear()

        log_file = tmp_path / "pipeline.log"

        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}, clear=False):
            logger = setup_pipeline_logging(log_file=log_file, level=logging.INFO)

            # Should be DEBUG level (from env var)
            assert logger.level == logging.DEBUG

    def test_setup_logging_with_log_level_env_var_warning(self, tmp_path):
        """Test that LOG_LEVEL=WARNING works."""
        # Clear any existing handlers
        logging.getLogger().handlers.clear()

        log_file = tmp_path / "pipeline.log"

        with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}, clear=False):
            logger = setup_pipeline_logging(log_file=log_file, level=logging.INFO)

            # Should be WARNING level (from env var)
            assert logger.level == logging.WARNING

    def test_setup_logging_fallback_to_param_level(self, tmp_path):
        """Test that level parameter is used when LOG_LEVEL not set."""
        # Clear any existing handlers
        logging.getLogger().handlers.clear()

        log_file = tmp_path / "pipeline.log"

        with patch.dict(os.environ, {}, clear=True):
            logger = setup_pipeline_logging(log_file=log_file, level=logging.WARNING)

            # Should be WARNING level (from parameter)
            assert logger.level == logging.WARNING

    def test_setup_logging_format_includes_level(self, tmp_path):
        """Test that log format includes level indicator."""
        # Clear any existing handlers
        logging.getLogger().handlers.clear()

        log_file = tmp_path / "pipeline.log"

        logger = setup_pipeline_logging(log_file=log_file, level=logging.INFO)

        # Get handler and check format
        handler = logger.handlers[0]
        formatter = handler.formatter

        # Format should include level indicator
        assert "[%(levelname)s]" in formatter._fmt
        assert "[%(asctime)s]" in formatter._fmt

        # Test actual output
        logger.info("Test message")
        handler.flush()

        # Read log file and check format
        if log_file.exists():
            content = log_file.read_text()
            assert "[INFO]" in content
            assert "Test message" in content

    def test_setup_logging_auto_detects_docker(self, tmp_path):
        """Test that Docker mode is auto-detected from LOG_DIR."""
        # Clear any existing handlers
        logging.getLogger().handlers.clear()

        with patch.dict(os.environ, {"LOG_DIR": str(tmp_path)}, clear=False):
            logger = setup_pipeline_logging(level=logging.INFO)

            # Should have TimedRotatingFileHandler (Docker mode)
            handlers = logger.handlers
            assert len(handlers) == 1
            from logging.handlers import TimedRotatingFileHandler

            assert isinstance(handlers[0], TimedRotatingFileHandler)

            # Log file should be created
            log_file = tmp_path / "pipeline.log"
            assert log_file.exists() or handlers[0].baseFilename == str(log_file)


class TestCleanupOldLogs:
    """Test log cleanup functionality."""

    def test_cleanup_old_logs_deletes_old_files(self, tmp_path):
        """Test that cleanup deletes files older than retention period."""
        # Create old log file (simulate by setting mtime)
        old_file = tmp_path / "pipeline.log.2025-01-01"
        old_file.write_text("old log content")

        # Set mtime to 100 days ago
        old_time = time.time() - (100 * 24 * 60 * 60)
        os.utime(old_file, (old_time, old_time))

        # Create recent log file
        recent_file = tmp_path / "pipeline.log.2026-01-20"
        recent_file.write_text("recent log content")

        # Run cleanup with 90 day retention
        cleanup_old_logs(tmp_path, retention_days=90)

        # Old file should be deleted
        assert not old_file.exists()

        # Recent file should remain
        assert recent_file.exists()

    def test_cleanup_old_logs_keeps_recent_files(self, tmp_path):
        """Test that cleanup keeps files within retention period."""
        # Create recent log file
        recent_file = tmp_path / "pipeline.log.2026-01-20"
        recent_file.write_text("recent log content")

        # Run cleanup with 90 day retention
        cleanup_old_logs(tmp_path, retention_days=90)

        # Recent file should remain
        assert recent_file.exists()

    def test_cleanup_old_logs_no_files(self, tmp_path):
        """Test that cleanup handles empty directory gracefully."""
        # Run cleanup on empty directory
        cleanup_old_logs(tmp_path, retention_days=90)

        # Should not raise any errors
        assert True

    def test_cleanup_old_logs_only_affects_log_files(self, tmp_path):
        """Test that cleanup only affects log files matching pattern."""
        # Create old log file
        old_log = tmp_path / "pipeline.log.2025-01-01"
        old_log.write_text("old log")
        old_time = time.time() - (100 * 24 * 60 * 60)
        os.utime(old_log, (old_time, old_time))

        # Create other file (should not be deleted)
        other_file = tmp_path / "other_file.txt"
        other_file.write_text("other content")
        os.utime(other_file, (old_time, old_time))

        # Run cleanup
        cleanup_old_logs(tmp_path, retention_days=90)

        # Log file should be deleted
        assert not old_log.exists()

        # Other file should remain
        assert other_file.exists()


class TestGetLogger:
    """Test logger retrieval."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger instance."""
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"


class TestShouldDisableTqdm:
    """Test tqdm disable detection."""

    def test_should_disable_tqdm_docker_mode(self):
        """Test that tqdm is disabled in Docker mode."""
        with patch.dict(os.environ, {"LOG_DIR": "/data/logs"}, clear=False):
            assert should_disable_tqdm() is True

    def test_should_disable_tqdm_terminal_mode(self):
        """Test that tqdm is not disabled in terminal mode."""
        with patch.dict(os.environ, {}, clear=True):
            assert should_disable_tqdm() is False

    def test_should_disable_tqdm_no_log_dir(self):
        """Test that tqdm is not disabled when LOG_DIR not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Explicitly remove LOG_DIR if it exists
            if "LOG_DIR" in os.environ:
                del os.environ["LOG_DIR"]
            assert should_disable_tqdm() is False


class TestLogLevelInteraction:
    """Test LOG_LEVEL and --debug flag interaction."""

    def test_log_level_env_var_overrides_default(self, tmp_path):
        """Test that LOG_LEVEL env var overrides default INFO level."""
        # Clear any existing handlers
        logging.getLogger().handlers.clear()

        log_file = tmp_path / "pipeline.log"

        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}, clear=False):
            logger = setup_pipeline_logging(log_file=log_file, level=logging.INFO)

            # Should be ERROR level (from env var, not default INFO)
            assert logger.level == logging.ERROR

    def test_debug_flag_can_override_log_level(self, tmp_path):
        """Test that --debug flag can override LOG_LEVEL (simulated)."""
        # Clear any existing handlers
        logging.getLogger().handlers.clear()

        log_file = tmp_path / "pipeline.log"

        with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}, clear=False):
            logger = setup_pipeline_logging(log_file=log_file, level=logging.INFO)

            # Initially WARNING from env var
            assert logger.level == logging.WARNING

            # Simulate --debug flag override (as done in phase main() functions)
            logger.setLevel(logging.DEBUG)

            # Should now be DEBUG
            assert logger.level == logging.DEBUG
