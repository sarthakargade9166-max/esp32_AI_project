from __future__ import annotations

# imports
import logging
import time
import serial

from serial_manager import SerialManager
from event_parser import EventParser
from queue_manager import QueueManager
from supabase_client import SupabaseClient
from logger import setup_logger, get_logger

# config
RECONNECT_INTERVAL: int = 3


# connect
def ensure_connection(sm: SerialManager, logger: logging.Logger) -> None:
    while not sm.is_connected():
        if sm.connect():
            break
        logger.warning(
            "Failed to connect to ESP32. Retrying in %ds...", RECONNECT_INTERVAL
        )
        time.sleep(RECONNECT_INTERVAL)


# main
def main() -> None:
    setup_logger()
    logger: logging.Logger = get_logger(__name__)

    # init
    sm: SerialManager = SerialManager()
    parser: EventParser = EventParser()
    queue: QueueManager = QueueManager()
    db: SupabaseClient = SupabaseClient()

    ensure_connection(sm, logger)
    logger.info("Application Started")

    # loop
    try:
        while True:
            try:
                raw_line: str | None = sm.read_line()
                if raw_line is None:
                    continue

                event: dict | None = parser.parse(raw_line)
                if event is None:
                    continue

                # update
                queue.process_event(event)
                db.insert_event(event)

                stats: dict = queue.get_statistics()

                print("\n========== STATS ==========")
                print(stats)
                print("===========================\n")

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
                queue.set_offline()
                db.update_status(queue.get_statistics())
                ensure_connection(sm, logger)

            except Exception as exc:
                logger.exception("Unexpected error in main processing loop: %s", exc)
                time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Application shutting down...")
    finally:
        sm.disconnect()
        queue.set_offline()
        db.update_status(queue.get_statistics())


if __name__ == "__main__":
    main()
