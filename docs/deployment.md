# Deployment & Setup Guide

This guide explains how to set up, configure, run, and troubleshoot the AI Smart Queue Prediction System from scratch.

---

## 1. System Requirements

- **Operating System:** Windows 10/11, macOS, or Linux
- **Python Version:** Python 3.10, 3.11, or 3.12
- **Hardware:** ESP32 Development Board, 2x VL53L0X Time-of-Flight sensors, Micro-USB data cable
- **Cloud Database:** Supabase Account (Free Tier)
- **Notifications (Optional):** Twilio WhatsApp Sandbox Account

---

## 2. Environment Setup

### Clone repository and create a virtual environment:
```bash
git clone https://github.com/your-username/esp32_AI_project.git
cd esp32_AI_project

python -m venv venv
```

### Activate virtual environment:
- **Windows (PowerShell):**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Linux / macOS:**
  ```bash
  source venv/bin/activate
  ```

### Install dependencies:
```bash
pip install -r requirements.txt
```

---

## 3. Environment Variables Configuration (`.env`)

Create a `.env` file in the root directory:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_API_KEY=your-supabase-anon-key

TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=whatsapp:+14155238886
MY_PHONE_NUMBER=whatsapp:+919876543210
```

---

## 4. Database Setup (Supabase)

Log in to your Supabase project dashboard, open the **SQL Editor**, and run:

```sql
CREATE TABLE IF NOT EXISTS queue_events (
    id BIGSERIAL PRIMARY KEY,
    timestamp BIGINT,
    event TEXT NOT NULL,
    queue_count INTEGER,
    device TEXT,
    firmware TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS queue_status (
    id INTEGER PRIMARY KEY DEFAULT 1,
    current_queue INTEGER DEFAULT 0,
    total_entries INTEGER DEFAULT 0,
    total_exits INTEGER DEFAULT 0,
    status TEXT DEFAULT 'OFFLINE',
    last_event TEXT,
    last_timestamp BIGINT,
    device TEXT,
    firmware TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE queue_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE queue_status ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access on queue_events" ON queue_events FOR SELECT USING (true);
CREATE POLICY "Allow public insert access on queue_events" ON queue_events FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow public read access on queue_status" ON queue_status FOR SELECT USING (true);
CREATE POLICY "Allow public all access on queue_status" ON queue_status FOR ALL USING (true);
```

---

## 5. ESP32 Hardware Setup & Flashing

1. Connect two VL53L0X distance sensors to your ESP32 board over I2C (SDA = GPIO 21, SCL = GPIO 22).
2. Open `Firmware/queue_counter_firmware.ino` in Arduino IDE.
3. Select board **ESP32 Dev Module** and choose your COM port.
4. Upload firmware to ESP32.
5. Verify serial monitor output at `115200` baud. It prints JSON formatted strings:
   `{"timestamp":1234,"event":"ENTER","count":1,"device":"ESP32","firmware":"1.0.0"}`

---

## 6. Model Training & Validation

Train the Random Forest model on historical data:

```bash
python ml/train_model.py
```
This cleans `ml/queue_data.csv`, trains the model, and creates `ml/models/model.pkl` and `ml/models/scaler.pkl`.

Validate model inference readiness:
```bash
python ml/test_model.py
```

---

## 7. Running the System

### Step 1: Start Backend Worker
Connect ESP32 via USB and start backend worker script:
```bash
python backend/main.py
```
This establishes serial connection, parses event logs, updates queue counts, and writes to Supabase.

### Step 2: Start Streamlit Dashboard
In a separate terminal window:
```bash
streamlit run dashboard/app.py
```
Open `http://localhost:8501` in your browser.

---

## 8. Common Errors & Troubleshooting

### Issue: `Could not open COM3` / Serial Exception
- **Cause:** ESP32 USB cable is disconnected or another program (Arduino Serial Monitor) is using the port.
- **Fix:** Close Arduino IDE Serial Monitor and check `backend/config.py` to ensure `SERIAL_PORT` matches your device port.

### Issue: `SUPABASE_URL or SUPABASE_KEY missing`
- **Cause:** Missing `.env` file or invalid key names.
- **Fix:** Verify `.env` exists in the root folder and contains `SUPABASE_URL` and `SUPABASE_API_KEY`.

### Issue: `Model Status: Not Loaded`
- **Cause:** Model file missing from `ml/models/`.
- **Fix:** Run `python ml/train_model.py` to train and generate `model.pkl`.
