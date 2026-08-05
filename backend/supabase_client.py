from __future__ import annotations

# imports
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

from logger import get_logger

logger = get_logger(__name__)

# config
_ENV_PATH: Path = Path(__file__).resolve().parent.parent / ".env"

TABLE_QUEUE_EVENTS: str = "queue_events"
TABLE_QUEUE_STATUS: str = "queue_status"
_STATUS_ROW_ID: int = 1


# client
class SupabaseClient:
    # init
    def __init__(self) -> None:
        self._client: Optional[Client] = None

        load_dotenv(dotenv_path=_ENV_PATH)

        url: Optional[str] = os.getenv("SUPABASE_URL")
        key: Optional[str] = os.getenv("SUPABASE_API_KEY") or os.getenv("SUPABASE_KEY")

        if not url or not key:
            logger.error("SUPABASE_URL or SUPABASE_KEY missing in environment.")
            return

        try:
            self._client = create_client(url, key)
            logger.info("Supabase client created successfully.")
        except Exception as exc:
            logger.error("Failed to create Supabase client: %s", exc)
            return

        if self.test_connection():
            logger.info("Supabase connection verified.")
        else:
            logger.warning("Supabase client created but connection test failed.")

    # insert
    def insert_event(self, event: Dict[str, Any]) -> bool:
        if not self._ensure_client():
            return False

        try:
            row: Dict[str, Any] = {
                "timestamp": event.get("timestamp"),
                "event": event.get("event"),
                "queue_count": event.get("count"),
                "device": event.get("device"),
                "firmware": event.get("firmware"),
            }

            self._client.table(TABLE_QUEUE_EVENTS).insert(row).execute()  # type: ignore[union-attr]
            logger.info("Inserted event: %s", row["event"])
            return True

        except Exception as exc:
            logger.error("Failed to insert event: %s", exc)
            return False

    # update
    def update_status(self, status: Dict[str, Any]) -> bool:
        if not self._ensure_client():
            return False

        try:
            row: Dict[str, Any] = {
                "id": _STATUS_ROW_ID,
                "current_queue": status.get("current_queue", 0),
                "total_entries": status.get("total_entries", 0),
                "total_exits": status.get("total_exits", 0),
                "status": status.get("status", "OFFLINE"),
                "last_event": status.get("last_event"),
                "last_timestamp": status.get("last_timestamp"),
                "device": status.get("device"),
                "firmware": status.get("firmware"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            (
                self._client  # type: ignore[union-attr]
                .table(TABLE_QUEUE_STATUS)
                .upsert(row, on_conflict="id")
                .execute()
            )

            logger.info("Updated queue_status — Queue: %s", row["current_queue"])
            return True

        except Exception as exc:
            logger.error("Failed to update queue_status: %s", exc)
            return False

    # fetch
    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        if not self._ensure_client():
            return []

        try:
            response = (
                self._client  # type: ignore[union-attr]
                .table(TABLE_QUEUE_EVENTS)
                .select("*")
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data if response.data else []

        except Exception as exc:
            logger.error("Failed to fetch recent events: %s", exc)
            return []

    # status
    def get_current_status(self) -> Optional[Dict[str, Any]]:
        if not self._ensure_client():
            return None

        try:
            response = (
                self._client  # type: ignore[union-attr]
                .table(TABLE_QUEUE_STATUS)
                .select("*")
                .eq("id", _STATUS_ROW_ID)
                .execute()
            )

            if response.data:
                return response.data[0]

            return None

        except Exception as exc:
            logger.error("Failed to fetch queue_status: %s", exc)
            return None

    # test
    def test_connection(self) -> bool:
        if not self._ensure_client():
            return False

        try:
            (
                self._client  # type: ignore[union-attr]
                .table(TABLE_QUEUE_STATUS)
                .select("id")
                .limit(1)
                .execute()
            )
            return True

        except Exception as exc:
            logger.error("Supabase connection test failed: %s", exc)
            return False

    # helper
    def _ensure_client(self) -> bool:
        if self._client is None:
            logger.error("Supabase client is not initialised.")
            return False
        return True


if __name__ == "__main__":
    client = SupabaseClient()
    print("Connected:", client.test_connection())
