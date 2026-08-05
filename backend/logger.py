from __future__ import annotations

# imports
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_logging_configured: bool = False

# config
LOG_DIR: Path = Path(__file__).resolve().parent / "logs"
LOG_FILE: Path = LOG_DIR / "queue_system.log"
MAX_BYTES: int = 5 * 1024 * 1024
BACKUP_COUNT: int = 5
LOG_FORMAT: str = "%(asctime)s | %(levelname)s | %(module)s | %(message)s"
DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"


# setup
def setup_logger(level: int = logging.DEBUG) -> None:
    global _logging_configured

    if _logging_configured:
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    # console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # file
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

    # thirdparty
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("hpack").setLevel(logging.WARNING)

    _logging_configured = True
    root_logger.info("Logging initialized successfully.")


# get
def get_logger(name: str) -> logging.Logger:
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
