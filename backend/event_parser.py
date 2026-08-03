"""
event_parser.py — JSON parsing and validation for ESP32 serial events.

Responsible for ONE thing only: turning a raw JSON string into a
validated Python dictionary.

Does NOT read from serial, update the queue, or access Supabase.
"""

import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

VALID_EVENTS: set = {"ENTER", "EXIT", "ONLINE", "TIMEOUT", "ERROR"}

EXPECTED_DEVICE: str = "ESP32"

REQUIRED_FIELDS: Dict[str, type] = {
    "timestamp": int,
    "event":     str,
    "count":     int,
    "device":    str,
    "firmware":  str,
}


class EventParser:
    """
    Parses and validates JSON event strings from the ESP32.

    Usage:
        parser = EventParser()
        result = parser.parse('{"timestamp":7735,"event":"ENTER","count":1,"device":"ESP32","firmware":"4.5"}')
    """

    def parse(self, raw_line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a raw string into a validated event dictionary.

        Returns the dict if valid, or None if the line is
        not JSON, malformed, or missing required fields.
        """
        data = self._decode_json(raw_line)
        if data is None:
            return None

        if not self._validate_fields(data):
            return None

        if not self._validate_event_type(data):
            return None

        if not self._validate_count(data):
            return None

        if not self._validate_device(data):
            return None

        if not self._validate_firmware(data):
            return None

        return data

    def _decode_json(self, raw_line: str) -> Optional[Dict[str, Any]]:
        """Attempt to decode a raw string as JSON."""
        line = raw_line.strip()

        if not line.startswith("{"):
            return None

        try:
            data = json.loads(line)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Malformed JSON: %s", e)
            return None

        if not isinstance(data, dict):
            logger.warning("JSON is not a dictionary")
            return None

        return data

    def _validate_fields(self, data: Dict[str, Any]) -> bool:
        """Check that all required fields exist and have correct types."""
        for field, expected_type in REQUIRED_FIELDS.items():
            if field not in data:
                logger.warning("Missing field: %s", field)
                return False
            if not isinstance(data[field], expected_type):
                logger.warning(
                    "Invalid type for '%s': expected %s, got %s",
                    field, expected_type.__name__, type(data[field]).__name__,
                )
                return False
        return True

    def _validate_event_type(self, data: Dict[str, Any]) -> bool:
        """Check that the event field contains a known event type."""
        if data["event"] not in VALID_EVENTS:
            logger.warning("Unknown event type: %s", data["event"])
            return False
        return True

    def _validate_count(self, data: Dict[str, Any]) -> bool:
        """Check that count is non-negative."""
        if data["count"] < 0:
            logger.warning("Negative count: %d", data["count"])
            return False
        return True

    def _validate_device(self, data: Dict[str, Any]) -> bool:
        """Check that the event came from the expected device."""
        if data["device"] != EXPECTED_DEVICE:
            logger.warning("Unexpected device: %s", data["device"])
            return False
        return True

    def _validate_firmware(self, data: Dict[str, Any]) -> bool:
        """Check that firmware version is a non-empty string."""
        if not data["firmware"].strip():
            logger.warning("Empty firmware version")
            return False
        return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    parser = EventParser()

    print("--- Valid Events ---")
    valid_enter = '{"timestamp":26670,"event":"ENTER","count":1,"device":"ESP32","firmware":"4.5"}'
    valid_online = '{"timestamp":7735,"event":"ONLINE","count":0,"device":"ESP32","firmware":"4.5"}'
    print(parser.parse(valid_enter))
    print(parser.parse(valid_online))

    print("\n--- Invalid Events ---")
    missing_fields = '{"event":"ENTER"}'
    bad_device = '{"timestamp":100,"event":"ENTER","count":1,"device":"Arduino","firmware":"1.0"}'
    bad_count = '{"timestamp":100,"event":"EXIT","count":-1,"device":"ESP32","firmware":"4.5"}'
    not_json = "A: 412mm VALID [CLEAR]"
    print(parser.parse(missing_fields))
    print(parser.parse(bad_device))
    print(parser.parse(bad_count))
    print(parser.parse(not_json))
