from __future__ import annotations

# imports
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


# analytics
def compute_queue_analytics(
    events: List[Dict[str, Any]],
    status: Optional[Dict[str, Any]] = None,
    current_prediction: Optional[float] = None,
) -> Dict[str, str]:
    # defaults
    results = {
        "peak_queue_today": "Not enough data",
        "avg_wait_time": "Not enough data",
        "busiest_hour": "Not enough data",
        "busiest_day": "Not enough data",
        "busiest_week": "Not enough data",
    }

    if not events:
        if status and "current_queue" in status:
            results["peak_queue_today"] = f"{status['current_queue']} People"
        if current_prediction is not None:
            results["avg_wait_time"] = f"{current_prediction:.1f} min"
        return results

    try:
        # dataframe
        df = pd.DataFrame(events)

        time_col = None
        for candidate in ["created_at", "timestamp"]:
            if candidate in df.columns:
                time_col = candidate
                df[candidate] = pd.to_datetime(df[candidate], errors="coerce")
                break

        # peak
        today_date = datetime.now().date()
        if time_col and not df[time_col].dropna().empty:
            df_today = df[df[time_col].dt.date == today_date]
            if not df_today.empty and "queue_count" in df_today.columns:
                results["peak_queue_today"] = f"{int(df_today['queue_count'].max())} People"
            elif "queue_count" in df.columns and not df["queue_count"].dropna().empty:
                results["peak_queue_today"] = f"{int(df['queue_count'].max())} People"
            elif status and "current_queue" in status:
                results["peak_queue_today"] = f"{status['current_queue']} People"
        elif status and "current_queue" in status:
            results["peak_queue_today"] = f"{status['current_queue']} People"

        # average
        if "queue_count" in df.columns and not df["queue_count"].dropna().empty:
            avg_queue = float(df["queue_count"].mean())
            calculated_wait = max(0.5, round(avg_queue * 2.5, 1))
            if current_prediction is not None:
                blended = round((calculated_wait + current_prediction) / 2.0, 1)
                results["avg_wait_time"] = f"{blended} min"
            else:
                results["avg_wait_time"] = f"{calculated_wait} min"
        elif current_prediction is not None:
            results["avg_wait_time"] = f"{current_prediction:.1f} min"

        # filter
        df_enter = df[df["event"].str.upper() == "ENTER"] if "event" in df.columns else df
        if df_enter.empty:
            df_enter = df

        if time_col and not df_enter[time_col].dropna().empty:
            valid_times = df_enter.dropna(subset=[time_col])

            # hour
            if not valid_times.empty:
                hours = valid_times[time_col].dt.hour
                top_hour = int(hours.mode().iloc[0]) if not hours.empty else None
                if top_hour is not None:
                    start_str = _format_12hr(top_hour)
                    end_str = _format_12hr((top_hour + 1) % 24)
                    results["busiest_hour"] = f"{start_str} – {end_str}"

            # day
            if not valid_times.empty:
                days = valid_times[time_col].dt.day_name()
                top_day = days.mode().iloc[0] if not days.empty else None
                if top_day:
                    results["busiest_day"] = str(top_day)

            # week
            if not valid_times.empty:
                week_of_month = ((valid_times[time_col].dt.day - 1) // 7 + 1).clip(lower=1, upper=5)
                top_week = int(week_of_month.mode().iloc[0]) if not week_of_month.empty else None
                if top_week is not None:
                    results["busiest_week"] = f"Week {top_week}"

    except Exception as exc:
        logger.exception("Error computing analytics: %s", exc)

    return results


# format
def _format_12hr(hour: int) -> str:
    if hour == 0:
        return "12 AM"
    elif hour < 12:
        return f"{hour} AM"
    elif hour == 12:
        return "12 PM"
    else:
        return f"{hour - 12} PM"


if __name__ == "__main__":
    sample_events = [
        {"created_at": "2026-08-05T08:15:00", "event": "ENTER", "queue_count": 5},
        {"created_at": "2026-08-05T09:30:00", "event": "ENTER", "queue_count": 12},
    ]
    out = compute_queue_analytics(sample_events, status={"current_queue": 8}, current_prediction=4.5)
    print("Analytics Output:", out)
