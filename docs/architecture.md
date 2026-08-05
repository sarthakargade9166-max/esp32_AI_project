# System Architecture

This project is an AI-based queue monitoring and wait-time prediction system. It uses an ESP32 microcontroller with VL53L0X Time-of-Flight sensors to track people entering and exiting a queue, records events in Supabase, predicts waiting time using a Random Forest model, and displays real-time status on a Streamlit dashboard.

---

## Data Flow Pipeline

The end-to-end flow moves from physical sensors to cloud database and machine learning inference:

```text
ESP32 (Hardware & VL53L0X Sensors)
        │
        ▼  (USB Serial Line / JSON Output)
SerialManager (backend/serial_manager.py)
        │
        ▼  (Raw JSON String)
EventParser (backend/event_parser.py)
        │
        ▼  (Validated Event Dictionary)
QueueManager (backend/queue_manager.py)
        │
        ▼  (Event Data & Updated State)
Supabase Client (backend/supabase_client.py)
        │
        ▼  (Cloud Tables: queue_events & queue_status)
Streamlit Dashboard (dashboard/app.py)
        │
        ▼  (Live Queue Status Dict)
Feature Builder (ml/feature_builder.py)
        │
        ▼  (Formatted 5-Feature Vector)
Queue Predictor (ml/predictor.py)
        │
        ▼  (Loaded model.pkl & scaler.pkl)
Predicted Wait Time (Displayed on Dashboard)
```

---

## Folder Structure

```text
esp32_AI_project/
├── .env                         # Environment variables (Supabase & Twilio credentials)
├── .gitignore                   # Excludes .env, logs, pycache, models
├── README.md                    # Project summary
├── backend/
│   ├── main.py                  # Backend orchestration entry point
│   ├── serial_manager.py        # Serial communication handler with ESP32
│   ├── event_parser.py          # JSON validation and event parser
│   ├── queue_manager.py        # In-memory queue state tracker
│   ├── supabase_client.py       # Supabase database client
│   ├── logger.py                # Centralized logging setup
│   └── config.py                # Serial COM port and baud rate configuration
├── dashboard/
│   ├── app.py                   # Streamlit dashboard UI (Dashboard & Developer pages)
│   └── analytics.py             # Analytics engine (Peak queue, busy hours/days)
├── ml/
│   ├── train_model.py           # Model training pipeline
│   ├── predictor.py             # Model inference module
│   ├── feature_builder.py       # Feature vector builder for live predictions
│   ├── test_model.py            # Deployment validation script
│   ├── queue_data.csv           # Historical dataset (100,000 clean rows)
│   └── models/
│       ├── model.pkl            # Trained RandomForestRegressor model
│       └── scaler.pkl           # Trained StandardScaler
├── notifications/
│   └── twilio_msg.py            # WhatsApp alert module using Twilio
├── Firmware/
│   ├── queue_counter_firmware.ino # ESP32 Arduino firmware
│   ├── config.h                 # Sensor threshold configuration
│   └── wiring.md                # Circuit connections and pin layout
└── docs/
    ├── architecture.md          # Architecture overview
    ├── api_reference.md         # API and class reference
    └── deployment.md            # Setup and deployment instructions
```

---

## Module Responsibilities

### 1. Hardware & Firmware (`Firmware/`)
The ESP32 reads distance measurements from two VL53L0X laser distance sensors placed at entry and exit points. When a person crosses a sensor threshold, the ESP32 determines directional movement (`ENTER` or `EXIT`), updates its local counter, and prints a JSON string to the USB serial interface.

### 2. Serial Manager (`backend/serial_manager.py`)
Connects to the ESP32 via PySerial using the configured COM port and baud rate. It reads incoming raw lines from the serial buffer, handles connection timeouts, and attempts automatic reconnection if the USB cable is unplugged.

### 3. Event Parser (`backend/event_parser.py`)
Decodes incoming serial strings as JSON and checks that all expected fields (`timestamp`, `event`, `count`, `device`, `firmware`) are present with valid data types. Malformed or unrecognized lines are logged and safely ignored.

### 4. Queue Manager (`backend/queue_manager.py`)
Maintains live state in memory. It tracks current queue count, total entries, total exits, system online status, and last event timestamp. It prevents negative queue counts.

### 5. Supabase Client (`backend/supabase_client.py`)
Persists data to Supabase PostgreSQL database tables:
- `queue_events`: Appends a new row for every detected event (`ENTER`, `EXIT`, `ONLINE`, `TIMEOUT`).
- `queue_status`: Upserts a single status row (`id=1`) with current queue size, entry/exit totals, device name, and timestamp.

### 6. Machine Learning Module (`ml/`)
- `train_model.py`: Cleans `queue_data.csv`, scales inputs using `StandardScaler`, splits data (64% train, 16% validation, 20% test), and trains a `RandomForestRegressor` (`n_estimators=200`, `max_depth=20`, `random_state=42`).
- `feature_builder.py`: Extracts the 5 feature inputs (`queue_count`, `avg_service_time`, `active_counters`, `hour_of_day`, `day_of_week`) from a live `queue_status` dictionary.
- `predictor.py`: Loads `model.pkl` and `scaler.pkl` once, transforms input vectors, and outputs predicted wait time in minutes.

### 7. Dashboard (`dashboard/`)
- `app.py`: Streamlit web dashboard with 2 navigation pages (`🏠 Dashboard` for end-user metrics, analytics, charts, and clean events; `🛠 Developer` for detailed device metrics, status table, logs, and system metadata).
- `analytics.py`: Computes historical trends from Supabase event logs (Peak Queue Today, Average Wait Time, Busiest Hour of Day, Busiest Day of Week, Busiest Week of Month).

### 8. Notifications (`notifications/twilio_msg.py`)
Provides a `send_whatsapp_message()` function to trigger WhatsApp alerts via Twilio API when specific queue thresholds or wait times are met.

---

## Database Design

### `queue_events` Table
Stores chronological event logs:
- `id` (bigint, primary key)
- `timestamp` (bigint)
- `event` (text: ENTER, EXIT, ONLINE, TIMEOUT)
- `queue_count` (integer)
- `device` (text)
- `firmware` (text)
- `created_at` (timestamptz, auto default now())

### `queue_status` Table
Stores single-row real-time system state (`id=1`):
- `id` (integer, primary key, value = 1)
- `current_queue` (integer)
- `total_entries` (integer)
- `total_exits` (integer)
- `status` (text: ONLINE, OFFLINE)
- `last_event` (text)
- `last_timestamp` (bigint)
- `device` (text)
- `firmware` (text)
- `updated_at` (timestamptz)
