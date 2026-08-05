from __future__ import annotations

# imports
import logging
import time
from typing import Optional

import serial

from config import SERIAL_PORT, BAUD_RATE

logger = logging.getLogger(__name__)

# config
READ_TIMEOUT: float = 1.0
RECONNECT_DELAY: int = 3


# serial
class SerialManager:
    # init
    def __init__(self) -> None:
        self._port_name: str = SERIAL_PORT
        self._baud_rate: int = BAUD_RATE
        self._connection: Optional[serial.Serial] = None

    # connect
    def connect(self) -> bool:
        try:
            self._connection = serial.Serial(
                port=self._port_name,
                baudrate=self._baud_rate,
                timeout=READ_TIMEOUT,
            )
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

    # disconnect
    def disconnect(self) -> None:
        if self._connection is not None:
            try:
                if self._connection.is_open:
                    self._connection.close()
                logger.info("Disconnected from ESP32")
            except Exception as e:
                logger.warning("Error while disconnecting: %s", e)
            finally:
                self._connection = None

    # reconnect
    def reconnect(self) -> None:
        logger.warning("Connection lost")
        self.disconnect()
        logger.info("Reconnecting...")

        while True:
            if self.connect():
                logger.info("Reconnected successfully")
                return
            logger.info("Retrying in %d seconds...", RECONNECT_DELAY)
            time.sleep(RECONNECT_DELAY)

    # status
    def is_connected(self) -> bool:
        return self._connection is not None and self._connection.is_open

    # read
    def read_line(self) -> Optional[str]:
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
