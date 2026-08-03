"""
serial_manager.py — Reliable USB Serial communication with the ESP32.

Responsible for ONE thing only: reading raw lines from the ESP32.
Does NOT parse JSON, update the queue, or communicate with Supabase.
"""

import logging
import time
from typing import Optional

import serial

from config import SERIAL_PORT, BAUD_RATE

logger = logging.getLogger(__name__)

READ_TIMEOUT: float = 1.0
RECONNECT_DELAY: int = 3
FLUSH_DURATION: float = 2.0


class SerialManager:
    """
    Manages the serial connection to the ESP32.

    Methods:
        connect()      — Open port, flush startup garbage, return True/False.
        disconnect()   — Safely close the port.
        reconnect()    — Block and retry until the ESP32 is back.
        is_connected() — Return True if the port is open.
        read_line()    — Return one raw line, or None. Does NOT reconnect.
    """

    def __init__(self) -> None:
        self._port_name: str = SERIAL_PORT
        self._baud_rate: int = BAUD_RATE
        self._connection: Optional[serial.Serial] = None

    def connect(self) -> bool:
        """Open the serial port and flush ESP32 boot garbage."""
        try:
            self._connection = serial.Serial(
                port=self._port_name,
                baudrate=self._baud_rate,
                timeout=READ_TIMEOUT,
            )
            self._flush_startup_garbage()
            logger.info(
                "Connected to ESP32 on %s @ %d baud",
                self._port_name, self._baud_rate,
            )
            return True

        except serial.SerialException as e:
            logger.error("Could not open %s: %s", self._port_name, e)
            self._connection = None
            return False

        except Exception as e:
            logger.error("Unexpected error during connect: %s", e)
            self._connection = None
            return False

    def disconnect(self) -> None:
        """Safely close the serial connection."""
        if self._connection is not None:
            try:
                if self._connection.is_open:
                    self._connection.close()
                logger.info("Disconnected from ESP32")
            except Exception as e:
                logger.warning("Error while disconnecting: %s", e)
            finally:
                self._connection = None

    def reconnect(self) -> None:
        """Block and retry every RECONNECT_DELAY seconds until reconnected."""
        logger.warning("Connection lost")
        self.disconnect()
        logger.info("Reconnecting...")

        while True:
            if self.connect():
                logger.info("Reconnected successfully")
                return
            logger.info("Retrying in %d seconds...", RECONNECT_DELAY)
            time.sleep(RECONNECT_DELAY)

    def is_connected(self) -> bool:
        """Return True if the serial port is open."""
        return self._connection is not None and self._connection.is_open

    def read_line(self) -> Optional[str]:
        """
        Read one line from the ESP32.

        Returns the raw string (no JSON parsing), or None on
        timeout / error. Does NOT reconnect — the caller decides.
        """
        if not self.is_connected():
            return None

        try:
            raw_bytes: bytes = self._connection.readline()
            if not raw_bytes:
                return None

            line: str = raw_bytes.decode("utf-8").strip()
            return line if line else None

        except serial.SerialException as e:
            logger.error("Serial error during read: %s", e)
            return None

        except UnicodeDecodeError:
            logger.warning("Received garbled data (decode error)")
            return None

        except Exception as e:
            logger.error("Unexpected error in read_line: %s", e)
            return None

    def _flush_startup_garbage(self) -> None:
        """Drain ESP32 boot/calibration output so the caller gets clean data."""
        if self._connection is None:
            return

        self._connection.reset_input_buffer()

        deadline: float = time.monotonic() + FLUSH_DURATION
        discarded: int = 0

        while time.monotonic() < deadline:
            try:
                if self._connection.readline():
                    discarded += 1
            except Exception:
                break

        if discarded > 0:
            logger.debug("Discarded %d startup lines", discarded)
