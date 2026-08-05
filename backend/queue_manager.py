from __future__ import annotations

# imports
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


# manager
class QueueManager:
    # init
    def __init__(self) -> None:
        self._current_queue: int = 0
        self._total_entries: int = 0
        self._total_exits: int = 0
        self._last_event: Optional[str] = None
        self._last_timestamp: Optional[int] = None
        self._device: Optional[str] = None
        self._firmware: Optional[str] = None
        self._status: str = "OFFLINE"

    # process
    def process_event(self, event: Optional[Dict[str, Any]]) -> None:
        if event is None:
            return

        try:
            event_type: str = event["event"]
            self._last_event = event_type
            self._last_timestamp = event.get("timestamp")

            self.set_online()

            if event.get("device"):
                self._device = event["device"]

            if event.get("firmware"):
                self._firmware = event["firmware"]

            if event_type == "ENTER":
                self._total_entries += 1
                self._current_queue = event.get("count", self._current_queue)
                logger.info("ENTER — Queue: %d", self._current_queue)

            elif event_type == "EXIT":
                self._total_exits += 1
                self._current_queue = event.get("count", self._current_queue)
                logger.info("EXIT — Queue: %d", self._current_queue)

            elif event_type == "ONLINE":
                logger.info(
                    "ONLINE — Device: %s, Firmware: %s",
                    self._device, self._firmware,
                )

            elif event_type == "TIMEOUT":
                logger.info("TIMEOUT — Queue unchanged: %d", self._current_queue)

            elif event_type == "ERROR":
                logger.warning("ERROR event received at timestamp %d", self._last_timestamp)

            else:
                logger.warning("Unhandled event type: %s", event_type)

        except (KeyError, TypeError) as e:
            logger.error("Failed to process event: %s", e)

    # getters
    def get_current_queue(self) -> int:
        return self._current_queue

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "current_queue": self._current_queue,
            "total_entries": self._total_entries,
            "total_exits": self._total_exits,
            "last_event": self._last_event,
            "last_timestamp": self._last_timestamp,
            "device": self._device,
            "firmware": self._firmware,
            "status": self._status,
        }

    def get_last_event(self) -> Optional[str]:
        return self._last_event

    # reset
    def reset(self) -> None:
        self._current_queue = 0
        self._total_entries = 0
        self._total_exits = 0
        self._last_event = None
        self._last_timestamp = None
        self._device = None
        self._firmware = None
        self._status = "OFFLINE"
        logger.info("QueueManager reset")

    # state
    def set_online(self) -> None:
        self._status = "ONLINE"

    def set_offline(self) -> None:
        self._status = "OFFLINE"

    def is_online(self) -> bool:
        return self._status == "ONLINE"


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    qm = QueueManager()

    test_events = [
        {"timestamp": 1000, "event": "ONLINE",  "count": 0, "device": "ESP32", "firmware": "4.5"},
        {"timestamp": 2000, "event": "ENTER",   "count": 1, "device": "ESP32", "firmware": "4.5"},
    ]

    for event in test_events:
        qm.process_event(event)
        print(qm.get_statistics())
