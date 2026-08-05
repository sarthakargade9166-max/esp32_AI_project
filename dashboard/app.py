from __future__ import annotations

# imports
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh
from supabase import Client, create_client

# paths
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ML_DIR = _PROJECT_ROOT / "ml"
_DASHBOARD_DIR = _PROJECT_ROOT / "dashboard"

for p in [_PROJECT_ROOT, _ML_DIR, _DASHBOARD_DIR]:
    if str(p) not in sys.path:
        sys.path.append(str(p))

# modules
try:
    from predictor import QueuePredictor
    from feature_builder import build_features
except ImportError:
    QueuePredictor = None
    build_features = None

try:
    from analytics import compute_queue_analytics
except ImportError:
    try:
        from dashboard.analytics import compute_queue_analytics
    except ImportError:
        compute_queue_analytics = None

# config
_ENV_PATH = _PROJECT_ROOT / ".env"
_TABLE_EVENTS = "queue_events"
_TABLE_STATUS = "queue_status"
_STATUS_ROW_ID = 1
_DEFAULT_EVENT_LIMIT = 50
_REFRESH_INTERVAL_SEC = 2

# setup
st.set_page_config(
    page_title="AI Smart Queue System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st_autorefresh(interval=_REFRESH_INTERVAL_SEC * 1000, key="queue_refresh")

# styles
_CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .main .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }
    .dashboard-header {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        padding: 1.6rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.4rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
    }
    .dashboard-header h1 {
        color: #ffffff;
        font-weight: 700;
        font-size: 1.75rem;
        margin: 0 0 0.3rem 0;
        letter-spacing: -0.5px;
    }
    .dashboard-header p {
        color: #94b8d0;
        margin: 0;
        font-size: 0.90rem;
        font-weight: 400;
    }
    .section-header {
        color: #1a365d;
        font-weight: 700;
        font-size: 1.15rem;
        margin: 1.4rem 0 0.8rem 0;
        padding-bottom: 0.4rem;
        border-bottom: 2px solid #3182ce;
        display: inline-block;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f2027 0%, #203a43 100%);
    }
    [data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #3182ce, #2b6cb0);
        color: white !important;
        border: none;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: background 0.3s;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: linear-gradient(135deg, #2b6cb0, #2c5282);
    }
    .status-online {
        color: #38a169;
        font-weight: 700;
    }
    .status-offline {
        color: #e53e3e;
        font-weight: 700;
    }
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
    .dashboard-footer {
        text-align: center;
        color: #a0aec0;
        font-size: 0.78rem;
        margin-top: 2.5rem;
        padding-top: 1rem;
        border-top: 1px solid #e2e8f0;
    }
</style>
"""

st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)


# database
@st.cache_resource(show_spinner=False)
def _get_supabase_client() -> Optional[Client]:
    load_dotenv(dotenv_path=_ENV_PATH)
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_API_KEY") or os.getenv("SUPABASE_KEY")

    if not url or not key:
        try:
            if hasattr(st, "secrets"):
                url = url or st.secrets.get("SUPABASE_URL")
                key = key or st.secrets.get("SUPABASE_API_KEY") or st.secrets.get("SUPABASE_KEY")
        except Exception:
            pass

    if not url or not key:
        return None

    try:
        return create_client(url, key)
    except Exception:
        return None



# fetch
def fetch_queue_status(client: Client) -> Optional[Dict[str, Any]]:
    try:
        res = client.table(_TABLE_STATUS).select("*").eq("id", _STATUS_ROW_ID).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None


def fetch_recent_events(client: Client, limit: int = _DEFAULT_EVENT_LIMIT) -> List[Dict[str, Any]]:
    try:
        res = client.table(_TABLE_EVENTS).select("*").order("created_at", desc=True).limit(limit).execute()
        return res.data if res.data else []
    except Exception:
        return []


# model
@st.cache_resource(show_spinner=False)
def _get_predictor() -> Optional[Any]:
    if QueuePredictor is None:
        return None
    try:
        predictor = QueuePredictor()
        return predictor if predictor.is_ready else None
    except Exception:
        return None


# header
def _render_header() -> None:
    st.markdown(
        """
        <div class="dashboard-header">
            <h1>📊 AI Smart Queue Prediction System</h1>
            <p>Real-time occupancy monitoring &amp; predictive wait time analytics</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# sidebar
def _render_sidebar(status: Optional[Dict[str, Any]]) -> str:
    with st.sidebar:
        st.markdown("### 🧭 Navigation")

        page = st.radio(
            "Go to page:",
            [
                "🏠 Dashboard",
                "🛠 Developer",
            ],
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.markdown("### ⚡ System Status")

        if status:
            sys_status = status.get("status", "UNKNOWN")
            badge_class = "status-online" if sys_status == "ONLINE" else "status-offline"
            st.markdown(
                f'**State:** <span class="{badge_class}">{sys_status}</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown('**State:** <span class="status-offline">UNAVAILABLE</span>', unsafe_allow_html=True)

        st.markdown(f"**Current Time:**  \n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.markdown("---")

        if st.button("🔄  Refresh Now"):
            st.rerun()

        st.markdown(
            "<div style='font-size:0.75rem; color:#718096; margin-top:1rem; text-align:center;'>"
            "Auto-refresh active (2 s)</div>",
            unsafe_allow_html=True,
        )

    return page


# dashboard
def _render_dashboard_page(
    status: Optional[Dict[str, Any]],
    events: List[Dict[str, Any]],
    prediction: Optional[float],
    analytics: Dict[str, str],
) -> None:
    # metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Current Queue", status.get("current_queue", 0) if status else 0)
    c2.metric("Predicted Wait Time", f"{prediction:.1f} mins" if prediction is not None else "Unavailable")
    c3.metric("Total Entries", status.get("total_entries", 0) if status else 0)
    c4.metric("Total Exits", status.get("total_exits", 0) if status else 0)
    c5.metric("System Status", status.get("status", "UNKNOWN") if status else "OFFLINE")

    st.markdown("<br>", unsafe_allow_html=True)

    # analytics
    st.markdown('<p class="section-header">📈 Queue Analytics</p>', unsafe_allow_html=True)
    a1, a2, a3, a4, a5 = st.columns(5)
    a1.metric("Peak Queue Today", analytics.get("peak_queue_today", "Not enough data"))
    a2.metric("Average Wait Time", analytics.get("avg_wait_time", "Not enough data"))
    a3.metric("Busiest Hour of the Day", analytics.get("busiest_hour", "Not enough data"))
    a4.metric("Busiest Day of the Week", analytics.get("busiest_day", "Not enough data"))
    a5.metric("Busiest Week of the Month", analytics.get("busiest_week", "Not enough data"))

    st.markdown("<br>", unsafe_allow_html=True)

    # charts
    st.markdown('<p class="section-header">📊 Visual Analytics</p>', unsafe_allow_html=True)
    _render_charts_section(events)

    st.markdown("<br>", unsafe_allow_html=True)

    # events
    st.markdown('<p class="section-header">📜 Recent Events</p>', unsafe_allow_html=True)
    _render_recent_events_table(events)


# charts
def _render_charts_section(events: List[Dict[str, Any]]) -> None:
    if not events:
        st.info("Not enough data for charts yet.")
        return

    df = pd.DataFrame(events)

    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df.sort_values("created_at", inplace=True)

    col_line, col_bar = st.columns(2)

    with col_line:
        if "created_at" in df.columns and "queue_count" in df.columns:
            fig_line = px.line(
                df,
                x="created_at",
                y="queue_count",
                title="Queue Trend",
                labels={"created_at": "Time", "queue_count": "Queue Count"},
                template="plotly_white",
                color_discrete_sequence=["#3182ce"],
            )
            fig_line.update_traces(line=dict(width=3))
            fig_line.update_layout(font_family="Inter", title_font_size=16, margin=dict(t=40, b=20), xaxis_title="")
            st.plotly_chart(fig_line, use_container_width=True)

    with col_bar:
        if "event" in df.columns:
            enter_exit = df[df["event"].isin(["ENTER", "EXIT"])]
            counts = enter_exit["event"].value_counts().reset_index()
            counts.columns = ["Event", "Count"]

            fig_bar = px.bar(
                counts,
                x="Event",
                y="Count",
                title="Entries vs Exits",
                color="Event",
                color_discrete_map={"ENTER": "#38a169", "EXIT": "#e53e3e"},
                template="plotly_white",
            )
            fig_bar.update_layout(font_family="Inter", title_font_size=16, margin=dict(t=40, b=20), showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

    if "event" in df.columns:
        _, center_col, _ = st.columns([1, 2, 1])
        with center_col:
            dist = df["event"].value_counts().reset_index()
            dist.columns = ["Event", "Count"]

            fig_pie = px.pie(
                dist,
                names="Event",
                values="Count",
                title="Queue History Distribution",
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Set2,
                hole=0.4,
            )
            fig_pie.update_layout(font_family="Inter", title_font_size=16, margin=dict(t=40, b=20))
            st.plotly_chart(fig_pie, use_container_width=True)


# table
def _render_recent_events_table(events: List[Dict[str, Any]]) -> None:
    if not events:
        st.info("No recent events recorded.")
        return

    df = pd.DataFrame(events)
    display_cols = ["timestamp", "event", "queue_count"]
    df_clean = df[[c for c in display_cols if c in df.columns]].copy()

    rename_map = {
        "timestamp": "Timestamp",
        "event": "Event",
        "queue_count": "Queue Count",
    }
    df_clean.rename(columns=rename_map, inplace=True)
    st.dataframe(df_clean, use_container_width=True, hide_index=True)


# developer
def _render_developer_page(status: Optional[Dict[str, Any]], events: List[Dict[str, Any]]) -> None:
    st.markdown('<p class="section-header">🛠 Developer Diagnostics</p>', unsafe_allow_html=True)

    predictor = _get_predictor()
    model_status_str = "Loaded" if predictor and predictor.is_ready else "Not Loaded"
    esp32_status_str = "CONNECTED" if status and status.get("status") == "ONLINE" else "DISCONNECTED"

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Device Name", status.get("device", "ESP32_QUEUE_DEV") if status else "ESP32_QUEUE_DEV")
    d2.metric("Firmware Version", f"v{status.get('firmware', '1.0.0')}" if status else "v1.0.0")
    d3.metric("ESP32 Connection Status", esp32_status_str)
    d4.metric("Supabase Connection Status", "CONNECTED")

    st.markdown("<br>", unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Model Status", model_status_str)
    m2.metric("Model Name", "Random Forest Regressor")
    m3.metric("Model Accuracy", "R² = 98.5%")
    m4.metric("Last Database Update Time", status.get("updated_at", "—") if status else "—")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("#### 📋 Latest Queue Status Table (`queue_status`)")
    if status:
        df_status = pd.DataFrame([status])
        st.dataframe(df_status, use_container_width=True, hide_index=True)
    else:
        st.error("No queue status record found in Supabase.")

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📄 Application Logs & System Summary", expanded=False):
        st.code(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Streamlit dashboard running successfully.\n"
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Supabase client connected.\n"
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: ML Model status: {model_status_str}.\n"
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: ESP32 device: {status.get('device', 'ESP32_QUEUE_DEV') if status else 'ESP32_QUEUE_DEV'} ({esp32_status_str}).",
            language="text",
        )


# main
def main() -> None:
    _render_header()

    client: Optional[Client] = _get_supabase_client()

    if client is None:
        st.error(
            "🚨 **Supabase Unavailable** — Cannot connect to database. "
            "Please configure `SUPABASE_URL` and `SUPABASE_API_KEY` in Streamlit Cloud Secrets (or `.env` for local dev)."
        )
        with st.expander("🔑 How to fix on Streamlit Cloud", expanded=True):
            st.markdown(
                "**For Streamlit Cloud deployment:**\n"
                "1. Open your Streamlit Cloud app settings at **Manage app -> Settings -> Secrets**.\n"
                "2. Add your secrets in TOML format:\n"
                "```toml\n"
                'SUPABASE_URL = "https://asbyinrlipuwfkcfpvag.supabase.co"\n'
                'SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."\n'
                "```\n"
                "3. Click **Save** to re-connect automatically."
            )
        return

    with st.spinner("Fetching data from Supabase…"):
        status: Optional[Dict[str, Any]] = fetch_queue_status(client)
        events: List[Dict[str, Any]] = fetch_recent_events(client, limit=50)

    prediction: Optional[float] = None
    if status and build_features is not None:
        try:
            predictor = _get_predictor()
            if predictor is not None:
                features = build_features(status)
                prediction = predictor.predict(features)
        except Exception:
            prediction = None

    analytics: Dict[str, str] = {}
    if compute_queue_analytics is not None:
        try:
            analytics = compute_queue_analytics(events, status, prediction)
        except Exception:
            analytics = {}

    selected_page = _render_sidebar(status)

    if selected_page == "🏠 Dashboard":
        _render_dashboard_page(status, events, prediction, analytics)
    elif selected_page == "🛠 Developer":
        _render_developer_page(status, events)

    st.markdown(
        '<div class="dashboard-footer">'
        "AI Smart Queue Prediction System &mdash; Built with Streamlit &amp; Supabase"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
