# Architecture

This project is a smart queue monitoring system. It uses an ESP32 microcontroller with IR sensors to count how many people are standing in a queue, predicts how long someone would have to wait using a machine learning model, stores everything in a cloud database, and sends you a WhatsApp message when the queue is short enough.

Here's how all the pieces connect.


## How it works, end to end

The ESP32 sits at the queue location with two IR sensors — one at the entry, one at the exit. Every time someone walks in or out, it updates a counter. Every 30 seconds or so, it sends that count to Supabase (our cloud database) over Wi-Fi.

On the backend, a Python script pulls data from the database, feeds it into a trained Random Forest model, and predicts how long the wait will be. If the prediction says the wait is under 5 minutes, it automatically sends a WhatsApp message through Twilio to let you know it's a good time to go.

There's also a Streamlit dashboard where you can see the current queue status, today's analytics, and predictions for the best times to visit.


## The main components

**Hardware (the `hardware/` folder)**

This is the ESP32 firmware. The Arduino sketch `esp_32_queue_counter.ino` handles reading the IR sensors, keeping a running count, connecting to Wi-Fi, and posting data to Supabase. The `config.h` file stores Wi-Fi credentials and the Supabase URL/key. There's also a `wiring.md` that explains how to connect the sensors to the ESP32.

**Database (the `database/` folder)**

We use Supabase, which is basically hosted PostgreSQL with a REST API built in. The `queue_data` table stores each reading — the queue count, the predicted wait time, and a timestamp. `supabase_client.py` is meant to be a reusable client module (still a placeholder for now), and `supabase_test.py` is a quick script to check that the connection works by inserting a test row.

**ML Pipeline (the `ml/` folder)**

The machine learning side is pretty straightforward. `train_model.py` reads historical data from `queue_data.csv`, trains a Random Forest Regressor using scikit-learn, and saves the model as `model.pkl`. The features it uses are: current queue count, average service time, hour of the day, and day of the week. The target is the actual wait time in minutes.

After training, it runs a quick test prediction. If the predicted wait is under 5 minutes, it triggers a WhatsApp notification.

`predict.py` is a placeholder — it's meant to be a standalone prediction module that loads the saved model for real-time use.

**Notifications (the `notifications/` folder)**

Just one file here: `twilio_msg.py`. It has a `send_whatsapp_message()` function that uses the Twilio API to send a WhatsApp message. The credentials come from the `.env` file. Right now the message text and recipient number are hardcoded.

**Dashboard (`dashboard.py` at the root)**

A Streamlit app with three pages you can switch between using the sidebar:

- Live Dashboard — shows current queue count, service time, wait estimate, and today's entry/exit numbers
- Today's Analytics — people served, peak hours, max queue size, averages
- Predictions and Insights — busiest/least busy days, best times to visit, tomorrow's forecast

All the values on the dashboard are currently static (hardcoded numbers). The plan is to connect it to live Supabase data and the ML model.

There's also a `dashboard/` folder with `app.py` and `utils.py`, but those are empty placeholders for now.


## Project structure

```
esp32_AI_project/
├── .env                          # Twilio and Supabase credentials
├── .gitignore                    # Keeps .env out of git
├── README.md
├── requirements.txt
├── dashboard.py                  # Main Streamlit app
│
├── hardware/
│   ├── esp_32_queue_counter.ino  # ESP32 Arduino firmware
│   ├── config.h                  # Wi-Fi and API config
│   └── wiring.md                 # How to wire the sensors
│
├── ml/
│   ├── train_model.py            # Trains the model
│   ├── predict.py                # Prediction module (placeholder)
│   ├── model.pkl                 # Saved trained model
│   └── queue_data.csv            # Training data
│
├── database/
│   ├── schema.sql                # Table definitions
│   ├── supabase_client.py        # Supabase client (placeholder)
│   └── supabase_test.py          # Connection test
│
├── notifications/
│   └── twilio_msg.py             # WhatsApp alerts via Twilio
│
├── dashboard/
│   ├── app.py                    # (placeholder)
│   └── utils.py                  # (placeholder)
│
└── docs/
    ├── architecture.md           # This file
    ├── deployment.md             # Setup and deployment guide
    └── api_reference.md          # API docs
```


## Tech stack

- **Hardware:** ESP32 with IR break-beam sensors, programmed via Arduino IDE
- **Database:** Supabase (hosted PostgreSQL with auto-generated REST API)
- **ML:** scikit-learn Random Forest, pandas and NumPy for data handling
- **Notifications:** Twilio WhatsApp API, using their sandbox for development
- **Dashboard:** Streamlit
- **Secrets management:** python-dotenv, loading from a `.env` file


## Security notes

API keys and tokens live in the `.env` file, which is excluded from git via `.gitignore`. The Supabase key used is the anonymous (anon) key, which is safe to use client-side as long as you have Row Level Security policies set up on your tables. Twilio credentials are loaded through environment variables at runtime.

One thing to watch out for: the ESP32's `config.h` will contain your Wi-Fi password and Supabase key in plain text. Don't push that to a public repo.


## What's next

Some things that still need to be built or improved:

- Actually implement `predict.py` so the model can be used for real-time predictions
- Connect the dashboard to live data from Supabase instead of hardcoded values
- Build out the `dashboard/app.py` and `utils.py` modules
- Add an OLED or LCD display on the ESP32 so people at the location can see the queue count
- Support multiple queues with separate sensor pairs
- Set up automatic model retraining with fresh data from the database
- Deploy the dashboard somewhere accessible (Streamlit Cloud, a VPS, etc.)
