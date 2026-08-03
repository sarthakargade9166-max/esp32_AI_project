"""
supabase_client.py — Database communication layer for the Smart Queue System.

Responsible for ONE thing only: reading from and writing to Supabase.

Does NOT read serial, parse JSON, update QueueManager, configure logging,
run machine learning, build UI, or send notifications.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

from logger import get_logger

logger = get_logger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

_ENV_PATH: Path = Path(__file__).resolve().parent.parent / ".env"

TABLE_QUEUE_EVENTS: str = "queue_events"
TABLE_QUEUE_STATUS: str = "queue_status"

# Fixed primary-key value for the single-row queue_status table.
_STATUS_ROW_ID: int = 1


class SupabaseClient:
    """
    Manages all Supabase interactions for the Smart Queue System.

    Public methods:
        insert_event(event)           — Insert one row into queue_events.
        update_status(status)         — Upsert the single queue_status row.
        get_recent_events(limit=20)   — Fetch the latest events (desc order).
        get_current_status()          — Fetch the queue_status row.
        test_connection()             — Return True if Supabase is reachable.
    """

    # ──────────────────────────────────────────────────────────────
    # Initialization
    # ──────────────────────────────────────────────────────────────

    def __init__(self) -> None:
        """
        Load environment variables, create the Supabase client,
        and verify the connection on startup.
        """
        self._client: Optional[Client] = None

        # Load .env from the project root (one level above /backend).
        load_dotenv(dotenv_path=_ENV_PATH)

        url: Optional[str] = os.getenv("SUPABASE_URL")
        key: Optional[str] = os.getenv("SUPABASE_API_KEY")

        if not url or not key:
            logger.error(
                "SUPABASE_URL or SUPABASE_API_KEY not found in environment. "
                "Ensure a .env file exists at: %s",
                _ENV_PATH,
            )
            return

        try:
            self._client = create_client(url, key)
            logger.info("Supabase client created successfully.")
        except Exception as exc:
            logger.error("Failed to create Supabase client: %s", exc)
            return

        # Verify connectivity at startup.
        if self.test_connection():
            logger.info("Supabase connection verified.")
        else:
            logger.warning(
                "Supabase client created but connection test failed. "
                "Operations may fail until the database is reachable."
            )

    # ──────────────────────────────────────────────────────────────
    # Public Methods
    # ──────────────────────────────────────────────────────────────

    def insert_event(self, event: Dict[str, Any]) -> bool:
        """
        Insert a single queue event into the ``queue_events`` table.

        Args:
            event: A validated event dictionary from EventParser, e.g.::

                {
                    "timestamp": 26670,
                    "event": "ENTER",
                    "count": 1,
                    "device": "ESP32",
                    "firmware": "4.5"
                }

        Returns:
            True on successful insert, False on any failure.
        """
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
            logger.info(
                "Inserted event: %s at timestamp %s",
                row["event"],
                row["timestamp"],
            )
            return True

        except Exception as exc:
            logger.error("Failed to insert event: %s", exc)
            return False

    def update_status(self, status: Dict[str, Any]) -> bool:
        """
        Upsert the single row in ``queue_status`` with the latest statistics.

        Expects the dictionary returned by ``QueueManager.get_statistics()``::

            {
                "current_queue": int,
                "total_entries": int,
                "total_exits": int,
                "last_event": str | None,
                "last_timestamp": int | None,
                "device": str | None,
                "firmware": str | None,
                "status": str,
            }

        If the row does not exist it will be created; otherwise it will be
        updated in-place via Supabase upsert.

        Returns:
            True on success, False on any failure.
        """
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

            logger.info(
                "Updated queue_status — Queue: %s | Status: %s",
                row["current_queue"],
                row["status"],
            )
            return True

        except Exception as exc:
            logger.error("Failed to update queue_status: %s", exc)
            return False

    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Return the latest events from ``queue_events``, ordered by
        ``timestamp`` descending.

        Args:
            limit: Maximum number of rows to return (default 20).

        Returns:
            A list of event dictionaries, or an empty list on failure.
        """
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

    def get_current_status(self) -> Optional[Dict[str, Any]]:
        """
        Return the single-row ``queue_status`` dictionary.

        Returns:
            The status dictionary, or None if not found / on failure.
        """
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

            logger.warning("No queue_status row found.")
            return None

        except Exception as exc:
            logger.error("Failed to fetch queue_status: %s", exc)
            return None

    def test_connection(self) -> bool:
        """
        Lightweight connectivity check against Supabase.

        Performs a minimal ``SELECT`` on ``queue_status`` with a row limit of 1.

        Returns:
            True if Supabase responds, False otherwise.
        """
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

    # ──────────────────────────────────────────────────────────────
    # Private Helpers
    # ──────────────────────────────────────────────────────────────

    def _ensure_client(self) -> bool:
        """Return True if the internal Supabase client is initialised."""
        if self._client is None:
            logger.error("Supabase client is not initialised.")
            return False
        return True


# ══════════════════════════════════════════════════════════════════════════════
# Standalone smoke-test
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from logger import setup_logger

    setup_logger()

    print("=" * 60)
    print("  Supabase Client — Smoke Test")
    print("=" * 60)

    client = SupabaseClient()

    # ── 1. Connection ─────────────────────────────────────────────
    print("\n[1] Testing connection...")
    connected: bool = client.test_connection()
    print(f"    Connected: {connected}")

    if not connected:
        print("\n✗ Cannot reach Supabase. Aborting remaining tests.")
        raise SystemExit(1)

    # ── 2. Insert a dummy ENTER event ─────────────────────────────
    print("\n[2] Inserting dummy ENTER event...")
    dummy_event: Dict[str, Any] = {
        "timestamp": 26670,
        "event": "ENTER",
        "count": 1,
        "device": "ESP32",
        "firmware": "4.5",
    }
    inserted: bool = client.insert_event(dummy_event)
    print(f"    Inserted: {inserted}")

    # ── 3. Read latest events ─────────────────────────────────────
    print("\n[3] Fetching recent events...")
    events: List[Dict[str, Any]] = client.get_recent_events(limit=5)
    for idx, evt in enumerate(events, start=1):
        print(f"    {idx}. {evt}")

    # ── 4. Update queue_status ────────────────────────────────────
    print("\n[4] Upserting queue_status...")
    dummy_status: Dict[str, Any] = {
        "current_queue": 1,
        "total_entries": 1,
        "total_exits": 0,
        "last_event": "ENTER",
        "last_timestamp": 26670,
        "device": "ESP32",
        "firmware": "4.5",
        "status": "ONLINE",
    }
    updated: bool = client.update_status(dummy_status)
    print(f"    Updated: {updated}")

    # ── 5. Read queue_status ──────────────────────────────────────
    print("\n[5] Fetching current queue_status...")
    current: Optional[Dict[str, Any]] = client.get_current_status()
    if current:
        for key, value in current.items():
            print(f"    {key}: {value}")
    else:
        print("    No status row found.")

    print("\n" + "=" * 60)
    print("  Smoke Test Complete")
    print("=" * 60)
