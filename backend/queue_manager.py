"""
queue_manager.py — Application state management for the queue system.

Responsible for ONE thing only: maintaining the current queue state
based on validated event dictionaries from event_parser.py.

Does NOT read from serial, parse JSON, access Supabase, or send notifications.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Maintains the live queue state for the Smart Queue system.

    Methods:
        process_event(event) — Update state based on a validated event dict.
        get_current_queue()  — Return the current queue count.
        get_statistics()     — Return a full snapshot of all state.
        get_last_event()     — Return the last event type string.
        reset()              — Reset all counters to zero.
        set_online()         — Mark the system as ONLINE.
        set_offline()        — Mark the system as OFFLINE.
        is_online()          — Return True if the system is ONLINE.
    """

    def __init__(self) -> None:
        self._current_queue: int = 0
        self._total_entries: int = 0
        self._total_exits: int = 0
        self._last_event: Optional[str] = None
        self._last_timestamp: Optional[int] = None
        self._device: Optional[str] = None
        self._firmware: Optional[str] = None
        self._status: str = "OFFLINE"

    def process_event(self, event: Optional[Dict[str, Any]]) -> None:
        """
        Update the queue state based on a validated event dictionary.

        Safely ignores None (e.g., when event_parser returns None
        for invalid data). Never crashes on malformed input.
        """
        if event is None:
            return

        try:
            event_type: str = event["event"]
            self._last_event = event_type
            self._last_timestamp = event["timestamp"]

            if event_type == "ENTER":
                self._total_entries += 1
                self._current_queue = event["count"]
                logger.info("ENTER — Queue: %d", self._current_queue)

            elif event_type == "EXIT":
                self._total_exits += 1
                self._current_queue = event["count"]
                logger.info("EXIT — Queue: %d", self._current_queue)

            elif event_type == "ONLINE":
                self._device = event.get("device")
                self._firmware = event.get("firmware")
                self.set_online()
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

    def get_current_queue(self) -> int:
        """Return the current number of people in the queue."""
        return self._current_queue

    def get_statistics(self) -> Dict[str, Any]:
        """Return a full snapshot of the queue state."""
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
        """Return the type of the last processed event."""
        return self._last_event

    def reset(self) -> None:
        """Reset all counters and state to initial values."""
        self._current_queue = 0
        self._total_entries = 0
        self._total_exits = 0
        self._last_event = None
        self._last_timestamp = None
        self._device = None
        self._firmware = None
        self._status = "OFFLINE"
        logger.info("QueueManager reset")

    def set_online(self) -> None:
        """Mark the system as ONLINE."""
        self._status = "ONLINE"

    def set_offline(self) -> None:
        """Mark the system as OFFLINE."""
        self._status = "OFFLINE"

    def is_online(self) -> bool:
        """Return True if the system is currently ONLINE."""
        return self._status == "ONLINE"


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    qm = QueueManager()

    test_events = [
        {"timestamp": 1000, "event": "ONLINE",  "count": 0, "device": "ESP32", "firmware": "4.5"},
        {"timestamp": 2000, "event": "ENTER",   "count": 1, "device": "ESP32", "firmware": "4.5"},
        {"timestamp": 3000, "event": "ENTER",   "count": 2, "device": "ESP32", "firmware": "4.5"},
        {"timestamp": 4000, "event": "EXIT",    "count": 1, "device": "ESP32", "firmware": "4.5"},
        {"timestamp": 5000, "event": "TIMEOUT", "count": 1, "device": "ESP32", "firmware": "4.5"},
        {"timestamp": 6000, "event": "ERROR",   "count": 1, "device": "ESP32", "firmware": "4.5"},
        None,
    ]

    for event in test_events:
        label = event["event"] if event else "None"
        print(f"\n--- Processing: {label} ---")
        qm.process_event(event)
        stats = qm.get_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value}")
