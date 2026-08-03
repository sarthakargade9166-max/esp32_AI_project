"""
main.py — Main orchestration entry point for the Smart Queue System.

Coordinates SerialManager, EventParser, QueueManager, SupabaseClient,
and logger modules.
Does NOT handle business logic or hardware directly.
"""

import logging
import time
import serial

from serial_manager import SerialManager
from event_parser import EventParser
from queue_manager import QueueManager
from supabase_client import SupabaseClient
from logger import setup_logger, get_logger

RECONNECT_INTERVAL: int = 3


def ensure_connection(sm: SerialManager, logger: logging.Logger) -> None:
    """Blocks and retries until a successful serial connection is established."""
    while not sm.is_connected():
        if sm.connect():
            break
        logger.warning(
            "Failed to connect to ESP32. Retrying in %ds...", RECONNECT_INTERVAL
        )
        time.sleep(RECONNECT_INTERVAL)


def main() -> None:
    """Main application loop orchestrating serial reading, parsing, and queue state."""
    setup_logger()
    logger: logging.Logger = get_logger(__name__)

    sm: SerialManager = SerialManager()
    parser: EventParser = EventParser()
    queue: QueueManager = QueueManager()
    db: SupabaseClient = SupabaseClient()

    ensure_connection(sm, logger)
    logger.info("Application Started")

    try:
        while True:
            try:
                raw_line: str | None = sm.read_line()
                if raw_line is None:
                    continue

                event: dict | None = parser.parse(raw_line)
                if event is None:
                    continue

                queue.process_event(event)
                db.insert_event(event)

                stats: dict = queue.get_statistics()
                db.update_status(stats)

                logger.debug(
                    "Current Queue: %d | Entries: %d | Exits: %d | Last Event: %s",
                    stats["current_queue"],
                    stats["total_entries"],
                    stats["total_exits"],
                    stats["last_event"],
                )

            except serial.SerialException as exc:
                logger.error("Serial communication error: %s", exc)
                sm.disconnect()
                ensure_connection(sm, logger)

            except Exception as exc:
                logger.exception("Unexpected error in main processing loop: %s", exc)
                time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Application shutting down...")
    finally:
        sm.disconnect()


if __name__ == "__main__":
    main()
