# API Reference

This document covers the public methods, classes, parameters, return values, and exceptions for all backend, machine learning, analytics, and notification modules in the project.

---

## Backend Modules

### 1. `backend/serial_manager.py`

#### Class `SerialManager`
Manages the PySerial USB connection to the ESP32 microcontroller.

##### `__init__() -> None`
Initializes port name and baud rate from `config.py`.

##### `connect() -> bool`
Opens the serial port.
- **Returns:** `True` if connected successfully, `False` on error.
- **Exceptions Caught:** `serial.SerialException`, `Exception`.

##### `disconnect() -> None`
Closes the active serial port safely.

##### `reconnect() -> None`
Blocks and retries connecting every 3 seconds until reestablished.

##### `is_connected() -> bool`
Checks if serial port is open.
- **Returns:** `True` if open, `False` otherwise.

##### `read_line() -> Optional[str]`
Reads one line from the serial buffer.
- **Returns:** Cleaned string line or `None` on timeout/error.
- **Exceptions Caught:** `serial.SerialException`, `UnicodeDecodeError`.

---

### 2. `backend/event_parser.py`

#### Class `EventParser`
Parses and validates raw JSON strings received over serial.

##### `parse(raw_line: str) -> Optional[Dict[str, Any]]`
Decodes JSON and validates fields.
- **Parameters:** `raw_line` (str): Raw string from serial.
- **Returns:** Event dictionary or `None` if invalid.
- **Expected Keys:** `timestamp` (int), `event` (str), `count` (int), `device` (str), `firmware` (str).

---

### 3. `backend/queue_manager.py`

#### Class `QueueManager`
Tracks in-memory queue state and statistics.

##### `process_event(event: Optional[Dict[str, Any]]) -> None`
Updates internal state based on validated event dictionary (`ENTER`, `EXIT`, `ONLINE`, `TIMEOUT`).

##### `get_current_queue() -> int`
Returns current queue count.

##### `get_statistics() -> Dict[str, Any]`
Returns state dictionary containing `current_queue`, `total_entries`, `total_exits`, `last_event`, `last_timestamp`, `device`, `firmware`, and `status`.

##### `reset() -> None`
Resets all counters and status to default offline values.

##### `set_online() -> None` / `set_offline() -> None`
Updates status string to `ONLINE` or `OFFLINE`.

---

### 4. `backend/supabase_client.py`

#### Class `SupabaseClient`
Handles database reads and writes to Supabase cloud PostgreSQL.

##### `__init__() -> None`
Loads environment credentials from `.env` and initializes `create_client`.

##### `insert_event(event: Dict[str, Any]) -> bool`
Inserts one event record into `queue_events`.
- **Returns:** `True` on success, `False` on error.

##### `update_status(status: Dict[str, Any]) -> bool`
Upserts status statistics into single row (`id=1`) of `queue_status`.
- **Returns:** `True` on success, `False` on error.

##### `get_recent_events(limit: int = 20) -> List[Dict[str, Any]]`
Queries `queue_events` ordered by timestamp descending.

##### `get_current_status() -> Optional[Dict[str, Any]]`
Fetches row `id=1` from `queue_status`.

##### `test_connection() -> bool`
Performs test SELECT query on `queue_status`.

---

### 5. `backend/logger.py`

##### `setup_logger(level: int = logging.DEBUG) -> None`
Configures root logger with console handler and rotating file handler (`logs/queue_system.log`).

##### `get_logger(name: str) -> logging.Logger`
Returns named logger instance.

---

### 6. `backend/main.py`

##### `ensure_connection(sm: SerialManager, logger: logging.Logger) -> None`
Retries serial connection until active.

##### `main() -> None`
Main event loop reading serial lines, parsing events, updating state, and saving to Supabase.

---

## Machine Learning Modules

### 1. `ml/predictor.py`

#### Class `QueuePredictor`
Loads trained model artifacts and computes predictions.

##### `__init__(model_path=None, scaler_path=None, auto_load=True) -> None`
Resolves artifact paths and optionally calls `load_model()`.

##### `load_model() -> bool`
Loads `model.pkl` and `scaler.pkl` using `joblib`.
- **Returns:** `True` if model loaded successfully, `False` otherwise.

##### `predict(features) -> Optional[float]`
Transforms feature vector and runs model prediction.
- **Parameters:** `features`: DataFrame, numpy array, or list containing `[queue_count, avg_service_time, active_counters, hour_of_day, day_of_week]`.
- **Returns:** Predicted wait time in minutes (float) or `None`.

---

### 2. `ml/feature_builder.py`

##### `build_features(status: Optional[Dict[str, Any]]) -> pd.DataFrame`
Converts `queue_status` dictionary into 1-row feature DataFrame with columns:
`['queue_count', 'avg_service_time', 'active_counters', 'hour_of_day', 'day_of_week']`.

---

### 3. `ml/train_model.py`

##### `run_pipeline(csv_path: Path | None = None) -> None`
Executes data cleaning, splitting, scaling, RandomForestRegressor training, evaluation (MAE, RMSE, R²), and artifact saving (`models/model.pkl`, `models/scaler.pkl`).

---

## Analytics Module

### `dashboard/analytics.py`

##### `compute_queue_analytics(events, status=None, current_prediction=None) -> Dict[str, str]`
Computes 5 queue metrics:
- `peak_queue_today`
- `avg_wait_time`
- `busiest_hour`
- `busiest_day`
- `busiest_week`
Returns string dictionary; falls back to `"Not enough data"` when logs are sparse.

---

## Notification Module

### `notifications/twilio_msg.py`

##### `send_whatsapp_message(prediction: float) -> None`
Initializes Twilio Client using `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` from `.env` and sends a WhatsApp message with predicted wait time.
