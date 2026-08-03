"""
logger.py — Centralized logging configuration for the Smart Queue System.

Responsible for configuring the application-wide logging system once and
providing logger instances across all modules.

Does NOT handle serial communication, JSON parsing, queue state, or database operations.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_logging_configured: bool = False

LOG_DIR: Path = Path(__file__).resolve().parent / "logs"
LOG_FILE: Path = LOG_DIR / "queue_system.log"
MAX_BYTES: int = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT: int = 5
LOG_FORMAT: str = "%(asctime)s | %(levelname)s | %(module)s | %(message)s"
DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"


def setup_logger(level: int = logging.DEBUG) -> None:
    """
    Configures application-wide logging to console and rotating file.

    Guarantees initialization runs only once to prevent duplicate log entries.
    Gracefully falls back to console-only logging if file system operations fail.

    Args:
        level: Logging threshold level (default: logging.DEBUG).
    """
    global _logging_configured

    if _logging_configured:
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Rotating File Handler with fallback
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=LOG_FILE,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except OSError as e:
        root_logger.warning(
            "Failed to initialize log file (%s). Falling back to console-only logging.", e
        )

    _logging_configured = True
    root_logger.info("Logging initialized successfully.")


def get_logger(name: str) -> logging.Logger:
    """
    Retrieves a logger instance for a given module name.

    Args:
        name: Name of the logger (typically __name__).

    Returns:
        logging.Logger: Configured logger object.
    """
    if not _logging_configured:
        setup_logger()
    return logging.getLogger(name)


if __name__ == "__main__":
    setup_logger()
    logger = get_logger(__name__)

    logger.debug("Debug message test")
    logger.info("Info message test")
    logger.warning("Warning message test")
    logger.error("Error message test")
    logger.critical("Critical message test")
