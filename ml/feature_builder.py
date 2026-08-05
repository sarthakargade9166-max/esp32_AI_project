from __future__ import annotations

# imports
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import pandas as pd

logger = logging.getLogger(__name__)

# schema
FEATURE_COLUMNS: List[str] = [
    "queue_count",
    "avg_service_time",
    "active_counters",
    "hour_of_day",
    "day_of_week",
]

# defaults
DEFAULT_AVG_SERVICE_TIME: float = 7.5
DEFAULT_ACTIVE_COUNTERS: int = 3


# builder
def build_features(status: Optional[Dict[str, Any]]) -> pd.DataFrame:
    if not status:
        status = {}

    # count
    raw_queue = status.get("current_queue", 0)
    try:
        queue_count: float = float(raw_queue) if raw_queue is not None else 0.0
    except (ValueError, TypeError):
        queue_count = 0.0

    # service
    raw_service = status.get("avg_service_time", DEFAULT_AVG_SERVICE_TIME)
    try:
        avg_service_time: float = float(raw_service) if raw_service is not None else DEFAULT_AVG_SERVICE_TIME
    except (ValueError, TypeError):
        avg_service_time = DEFAULT_AVG_SERVICE_TIME

    # counters
    raw_counters = status.get("active_counters", DEFAULT_ACTIVE_COUNTERS)
    try:
        active_counters: float = float(raw_counters) if raw_counters is not None else float(DEFAULT_ACTIVE_COUNTERS)
    except (ValueError, TypeError):
        active_counters = float(DEFAULT_ACTIVE_COUNTERS)

    # time
    now = datetime.now()
    if "last_timestamp" in status and status["last_timestamp"]:
        try:
            ts_str = str(status["last_timestamp"]).replace("Z", "")
            now = datetime.fromisoformat(ts_str)
        except Exception:
            now = datetime.now()

    # vector
    feature_dict: Dict[str, List[Union[int, float]]] = {
        "queue_count": [max(0.0, queue_count)],
        "avg_service_time": [max(0.1, avg_service_time)],
        "active_counters": [max(1.0, active_counters)],
        "hour_of_day": [now.hour],
        "day_of_week": [now.weekday()],
    }

    return pd.DataFrame(feature_dict)[FEATURE_COLUMNS]


if __name__ == "__main__":
    sample_status = {
        "current_queue": 8,
        "total_entries": 40,
        "total_exits": 32,
        "status": "ONLINE",
    }
    df_out = build_features(sample_status)
    print("Features:")
    print(df_out)
