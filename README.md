#  ESP32 AI Queue Monitoring & Wait-Time Prediction System

An end-to-end IoT and Machine Learning solution for real-time queue tracking and wait-time estimation. The system utilizes an **ESP32 microcontroller** with **VL53L0X Time-of-Flight (ToF) sensors** to detect physical entries and exits, streams event data to a **Python backend**, persists events in **Supabase PostgreSQL**, predicts waiting times using a **Random Forest Regressor**, displays live status on an interactive **Streamlit Dashboard**, and dispatches automated **WhatsApp notifications via Twilio**.

---

##  System Architecture

```text
ESP32 (Hardware & VL53L0X Sensors)
        │
        ▼ (Serial / USB line - JSON events)
SerialManager (backend/serial_manager.py)
        │
        ▼ (Raw JSON String)
EventParser (backend/event_parser.py)
        │
        ▼ (Validated Event Dict)
QueueManager (backend/queue_manager.py)
        │
        ▼ (Event Data & Queue State)
Supabase Client (backend/supabase_client.py)
        │
        ▼ (Cloud Tables: queue_events & queue_status)
Streamlit Dashboard (dashboard/app.py)
        │
        ▼ (Live Queue Status Dict)
Feature Builder (ml/feature_builder.py)
        │
        ▼ (5-Feature Input Vector)
Queue Predictor (ml/predictor.py)
        │
        ▼ (RandomForest Model Inference)
Predicted Wait Time (Displayed on Dashboard & Alerts via Twilio)
```

---

## Features

- ** Hardware Sensing**: ESP32 microcontroller with dual VL53L0X sensors to count directional movement (`ENTER` / `EXIT`).
- ** Robust Serial Ingestion**: Python serial listener with auto-reconnection and JSON message validation.
- ** In-Memory Queue State**: Real-time counter management preventing negative values and handling timeouts.
- ** Cloud Persistence**: Supabase PostgreSQL database maintaining event logs (`queue_events`) and single-row system status (`queue_status`).
- ** AI/ML Wait-Time Inference**: Trained `RandomForestRegressor` predicting waiting times in minutes based on active counters, queue depth, service rates, hour of day, and day of week.
- ** Interactive Streamlit Dashboard**: Multi-page dashboard with real-time queue metrics, analytics charts, and developer debugging tools.
- ** WhatsApp Alerts**: Twilio integration for automated queue alerts and threshold warnings.

---

##  Repository Structure

```text
esp32_AI_project/
├── .env                         # Environment variables (Supabase & Twilio credentials)
├── .gitignore                   # Ignored files (secrets, virtual environments, cache)
├── README.md                    # Project documentation
├── backend/                     # Python backend service
│   ├── main.py                  # Backend main entry point
│   ├── serial_manager.py        # Serial communication handler with ESP32
│   ├── event_parser.py          # JSON validation and event parser
│   ├── queue_manager.py        # In-memory queue state tracker
│   ├── supabase_client.py       # Supabase database integration
│   ├── logger.py                # Logging system configuration
│   └── config.py                # COM port and baud rate configurations
├── dashboard/                   # Streamlit web interface
│   ├── app.py                   # Main Streamlit web application
│   ├── analytics.py             # Historical queue analytics module
│   └── utils.py                 # Utility helpers
├── ml/                          # Machine Learning pipeline
│   ├── train_model.py           # Model training script
│   ├── predictor.py             # Model loading and inference engine
│   ├── feature_builder.py       # Live feature vector transformer
│   ├── test_model.py            # Deployment & validation script
│   ├── queue_simulator.py       # Synthetic event generator for testing
│   ├── queue_data.csv           # Historical dataset
│   └── models/                  # Trained model artifacts (.pkl)
├── notifications/               # Notification service
│   └── twilio_msg.py            # Twilio WhatsApp message dispatcher
├── Firmware/                    # ESP32 C++/Arduino code
│   ├── queue_counter_firmware.ino # Arduino sketch for ESP32 & VL53L0X
│   ├── config.h                 # Distance threshold settings
│   └── wiring.md                # Wiring diagram and pin mappings
└── docs/                        # Technical documentation
    ├── architecture.md          # Full system architecture
    ├── api_reference.md         # API & Class references
    └── deployment.md            # Detailed setup & deployment guide
```

---

##  Setup & Installation

### 1. Prerequisites

- **Python 3.9+** installed
- **ESP32 Development Board** & **2x VL53L0X ToF Sensors**
- **Supabase Account** (PostgreSQL Database)
- **Twilio Account** (optional, for WhatsApp messaging)

---

### 2. Clone Repository & Install Dependencies

```bash
git clone https://github.com/your-username/esp32_AI_project.git
cd esp32_AI_project

# Create a virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### 3. Environment Configuration (`.env`)

Create a `.env` file in the root directory:

```env
# Supabase Configuration
SUPABASE_URL=https://your-supabase-project-id.supabase.co
SUPABASE_KEY=your-supabase-anon-or-service-role-key

# Twilio Configuration (Optional)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
RECIPIENT_WHATSAPP_NUMBER=whatsapp:+1234567890

# Serial Configuration
SERIAL_PORT=COM3
BAUD_RATE=115200
```

---

##  Quick Start & Usage

### Step 1: Flash ESP32 Firmware
1. Open `Firmware/queue_counter_firmware.ino` in Arduino IDE.
2. Wire your VL53L0X sensors according to `Firmware/wiring.md`.
3. Select board **ESP32 Dev Module** and set Baud Rate to `115200`.
4. Upload sketch to ESP32.

---

### Step 2: Train Machine Learning Model (Optional)
If model artifacts (`ml/models/model.pkl` and `ml/models/scaler.pkl`) do not exist, run:

```bash
python ml/train_model.py
```

To verify inference accuracy:
```bash
python ml/test_model.py
```

---

### Step 3: Run Backend Service
Start the serial listener & database sync service:

```bash
python backend/main.py
```

---

### Step 4: Launch Streamlit Dashboard
Open a new terminal tab and start the dashboard:

```bash
streamlit run dashboard/app.py
```

Navigate to `http://localhost:8501` in your browser.

---

##  Database Tables (Supabase)

### 1. `queue_events` Table
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | bigint (PK) | Auto-incrementing ID |
| `timestamp` | bigint | Unix Epoch timestamp (ms) |
| `event` | text | Event type (`ENTER`, `EXIT`, `ONLINE`, `TIMEOUT`) |
| `queue_count` | integer | Active queue size |
| `device` | text | ESP32 device identifier |
| `firmware` | text | Firmware version |
| `created_at` | timestamptz | Auto timestamp |

### 2. `queue_status` Table
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | integer (PK) | Fixed single-row record (`id=1`) |
| `current_queue` | integer | Live queue count |
| `total_entries` | integer | Cumulative entries |
| `total_exits` | integer | Cumulative exits |
| `status` | text | `ONLINE` or `OFFLINE` |
| `last_event` | text | Latest event type |
| `last_timestamp`| bigint | Last update timestamp |
| `device` | text | Device name |
| `firmware` | text | Firmware version |
| `updated_at` | timestamptz | Status update timestamp |

---

##  License

This project is licensed under the **MIT License**.
