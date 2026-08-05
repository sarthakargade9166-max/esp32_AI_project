from __future__ import annotations

# imports
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# config
VALID_EVENTS: set = {"ENTER", "EXIT", "ONLINE", "TIMEOUT", "ERROR"}
EXPECTED_DEVICE: str = "ESP32"

REQUIRED_FIELDS: Dict[str, type] = {
    "timestamp": int,
    "event":     str,
    "count":     int,
    "device":    str,
    "firmware":  str,
}


# parser
class EventParser:
    # parse
    def parse(self, raw_line: str) -> Optional[Dict[str, Any]]:
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

    # decode
    def _decode_json(self, raw_line: str) -> Optional[Dict[str, Any]]:
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

    # validate
    def _validate_fields(self, data: Dict[str, Any]) -> bool:
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
        if data["event"] not in VALID_EVENTS:
            logger.warning("Unknown event type: %s", data["event"])
            return False
        return True

    def _validate_count(self, data: Dict[str, Any]) -> bool:
        if data["count"] < 0:
            logger.warning("Negative count: %d", data["count"])
            return False
        return True

    def _validate_device(self, data: Dict[str, Any]) -> bool:
        if data["device"] != EXPECTED_DEVICE:
            logger.warning("Unexpected device: %s", data["device"])
            return False
        return True

    def _validate_firmware(self, data: Dict[str, Any]) -> bool:
        if not data["firmware"].strip():
            logger.warning("Empty firmware version")
            return False
        return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    parser = EventParser()

    valid_enter = '{"timestamp":26670,"event":"ENTER","count":1,"device":"ESP32","firmware":"4.5"}'
    valid_online = '{"timestamp":7735,"event":"ONLINE","count":0,"device":"ESP32","firmware":"4.5"}'
    print(parser.parse(valid_enter))
    print(parser.parse(valid_online))
