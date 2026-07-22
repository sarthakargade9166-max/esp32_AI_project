# API Reference

This covers all the Python modules, the Supabase REST endpoints, and how the ESP32 communicates with the backend.


## ML Pipeline

### train_model.py

This is the main training script. When you run it, it:

1. Reads `queue_data.csv` from the current directory
2. Splits the data 80/20 for training and testing
3. Trains a Random Forest model with 100 estimators
4. Runs a test prediction with a hardcoded sample (queue count of 1, service time of 5 min, 11 AM on a Monday)
5. If the predicted wait is under 5 minutes, it imports `twilio_msg` and sends a WhatsApp alert

```bash
cd ml
python train_model.py
```

The features used are `queue_count`, `avg_service_time`, `hour_of_day`, and `day_of_week`. The target variable is `actual_wait` (in minutes).

### predict.py

Not implemented yet. This is meant to be a standalone module that loads `model.pkl` and exposes a prediction function for real-time use. Something like:

```python
def predict_wait_time(queue_count, avg_service_time, hour_of_day, day_of_week):
    # loads model.pkl and returns predicted wait in minutes
```


## Notifications

### twilio_msg.py

Has one function:

**`send_whatsapp_message(wait_time)`**

Sends a WhatsApp message through Twilio saying the wait is under 5 minutes. The `wait_time` parameter is accepted but isn't actually included in the message body right now — the message text is hardcoded.

It reads `twilio_acc_sid` and `twilio_auth_token` from the `.env` file using `python-dotenv`.

The sender is the Twilio sandbox number (`+14155238886`) and the recipient is hardcoded to `+917219699787`. To change the recipient, edit the `to` field in the function.

```python
from twilio_msg import send_whatsapp_message
send_whatsapp_message(3.5)
```


## Database

### supabase_test.py

A quick test script that connects to Supabase and inserts a sample row into the `queue_data` table. Uses a hardcoded URL and key (not from `.env`). Useful for checking that your Supabase project is reachable and the table exists.

```bash
cd database
python supabase_test.py
```

It inserts `{"queue_count": 15, "predicted_wait": 30}` and prints the response.

### supabase_client.py

Placeholder. Not implemented yet. This is meant to be a reusable module for reading and writing queue data from the rest of the codebase.


## Supabase REST API

Supabase auto-generates a REST API for your tables. Here's how the project uses it.

**Base URL:** `https://<your-project-id>.supabase.co/rest/v1/`

**Headers you need on every request:**

```
apikey: <your anon key>
Authorization: Bearer <your anon key>
Content-Type: application/json
```

**To insert a new reading:**

```
POST /rest/v1/queue_data

Body:
{
  "queue_count": 15,
  "predicted_wait": 30.0
}
```

Returns the inserted row with its auto-generated `id` and `created_at` timestamp.

**To fetch the latest readings:**

```
GET /rest/v1/queue_data?order=created_at.desc&limit=10
```

**To fetch readings from a specific day:**

```
GET /rest/v1/queue_data?created_at=gte.2026-07-22T00:00:00Z&created_at=lt.2026-07-23T00:00:00Z&order=created_at.asc
```


## Dashboard

### dashboard.py

The main Streamlit app. Has three pages you switch between using the sidebar:

**Live Dashboard** shows current queue (15), average service time (5 min), wait estimate (75 min), people entered (120), people exited (105), and alert status (Active).

**Today's Analytics** shows people served (105), peak hour (11 AM to 1 PM), max queue (32), average wait (18 min), average service (5 min), and total visitors (120).

**Predictions & Insights** shows busiest day (Monday), least busy day (Thursday), best time to visit (2 PM to 4 PM), predicted crowd tomorrow (Medium), expected wait tomorrow (10-20 min), and a recommendation.

All these values are hardcoded right now. They'll need to be connected to live data from Supabase and the ML model.

### dashboard/app.py and dashboard/utils.py

Both are empty placeholders.


## ESP32 HTTP Interface

The ESP32 firmware sends queue data to Supabase by making HTTP POST requests to the REST API.

It posts to:
```
POST https://<project>.supabase.co/rest/v1/queue_data
```

With the standard Supabase headers (apikey, Authorization, Content-Type) and a JSON body containing `queue_count` and `predicted_wait`.

The reporting interval is set in `config.h` and defaults to every 30 seconds. If the request fails (401, 403, 5xx), the ESP32 logs the error to Serial and keeps retrying.
