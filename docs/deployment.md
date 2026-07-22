# Deployment Guide

This walks you through setting up every part of the project — from the database and ESP32 hardware to the ML model, WhatsApp notifications, and the Streamlit dashboard.


## What you'll need

**Software:** Python 3.9 or newer, pip, Arduino IDE 2.x, and Git.

**Accounts:** You'll need a free account on [Supabase](https://supabase.com) for the database and [Twilio](https://www.twilio.com) for WhatsApp messaging. If you want to host the dashboard online, [Streamlit Cloud](https://streamlit.io/cloud) is a free option.

**Hardware:** An ESP32 dev board, two IR break-beam sensors (one for entry, one for exit), a breadboard with jumper wires, and a USB cable to program the ESP32.


## Setting up the Python environment

Clone the repo and create a virtual environment:

```bash
git clone <your-repo-url>
cd esp32_AI_project

python -m venv venv
venv\Scripts\activate        # on Windows
# source venv/bin/activate   # on Mac/Linux
```

Install the dependencies:

```bash
pip install streamlit pandas numpy scikit-learn twilio python-dotenv supabase
```

Then create a `.env` file in the project root with your credentials:

```
twilio_acc_sid = YOUR_TWILIO_ACCOUNT_SID
twilio_auth_token = YOUR_TWILIO_AUTH_TOKEN
supabase_api_key = YOUR_SUPABASE_ANON_KEY
```

Make sure `.env` is in your `.gitignore` so you don't accidentally push your keys to GitHub.


## Setting up Supabase

Go to [app.supabase.com](https://app.supabase.com), create a new project, and pick a region close to you.

Once the project is ready, open the SQL Editor and run this to create the table:

```sql
CREATE TABLE queue_data (
    id             BIGSERIAL    PRIMARY KEY,
    queue_count    INTEGER      NOT NULL,
    predicted_wait FLOAT,
    created_at     TIMESTAMPTZ  DEFAULT now()
);

ALTER TABLE queue_data ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anonymous inserts"
ON queue_data FOR INSERT
TO anon
WITH CHECK (true);

CREATE POLICY "Allow anonymous reads"
ON queue_data FOR SELECT
TO anon
USING (true);
```

To get your API credentials, go to Project Settings, then API. You'll need the Project URL and the anon/public key. Put the key in your `.env` file.

To test the connection:

```bash
cd database
python supabase_test.py
```

If it prints "Inserted Successfully" followed by the response data, you're good.


## Setting up the ESP32

**Install the board in Arduino IDE:**

1. Open Arduino IDE, go to File then Preferences
2. Add this URL to the Additional Board Manager URLs field: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
3. Then go to Tools, Board, Board Manager, search for "ESP32", and install it

**Fill in `config.h`:**

Open `hardware/config.h` and put in your Wi-Fi network name, password, and Supabase URL and key. Also set which GPIO pins your sensors are connected to.

**Wire the sensors:**

Check `hardware/wiring.md` for the full diagram. The short version: connect the entry sensor output to GPIO 4, the exit sensor output to GPIO 5, power them from 3.3V or 5V, and connect the grounds together.

**Upload the firmware:**

Connect the ESP32 over USB, select "ESP32 Dev Module" as the board in Arduino IDE, pick the right COM port, and hit upload. Open the Serial Monitor at 115200 baud to check that it connects to Wi-Fi and starts sending data.


## Training the ML model

The training data lives in `ml/queue_data.csv`. It has columns for queue count, average service time, hour of day, day of week, and the actual observed wait time.

To train:

```bash
cd ml
python train_model.py
```

This trains a Random Forest model and prints a sample prediction. If the predicted wait is under 5 minutes, it also sends a WhatsApp alert.

The trained model gets saved as `model.pkl` in the same folder.

If you want to retrain later with newer data, just export fresh data from Supabase, update the CSV, and run the script again.


## Setting up Twilio for WhatsApp

Sign up at [twilio.com](https://www.twilio.com) and grab your Account SID and Auth Token from the dashboard. Put them in your `.env` file.

To enable WhatsApp, go to Messaging, then "Try it Out", then "Send a WhatsApp message". It'll give you a join code — send that from your phone to the Twilio sandbox number (`+14155238886`) to connect.

If you want to change who receives the alerts, edit the phone number in `notifications/twilio_msg.py`:

```python
to="whatsapp:+91XXXXXXXXXX"
```

To test that it works:

```bash
cd notifications
python -c "from twilio_msg import send_whatsapp_message; send_whatsapp_message(3.5)"
```

You should get a WhatsApp message on your phone.


## Running the dashboard

```bash
streamlit run dashboard.py
```

It'll open in your browser at `http://localhost:8501`. Use the sidebar to switch between the three pages: Live Dashboard, Today's Analytics, and Predictions & Insights.


## Deploying to production

You have a few options here depending on what works best for you.

**Streamlit Community Cloud (free and easy)**

Push your project to a public GitHub repo. Go to [share.streamlit.io](https://share.streamlit.io), create a new app, point it to your repo, and set `dashboard.py` as the main file. Add your secrets (Twilio and Supabase credentials) in the Advanced Settings section. Hit deploy.

**On a VPS (AWS, DigitalOcean, etc.)**

Spin up a small Ubuntu server (1 vCPU, 1 GB RAM is enough). Install Python, clone the repo, set up a virtual environment, install dependencies, and create the `.env` file. Then run:

```bash
streamlit run dashboard.py --server.port 8501 --server.headless true
```

If you want it to stay running and restart automatically, you can set up a systemd service. If you want HTTPS, put Nginx in front of it as a reverse proxy and use Let's Encrypt for the SSL certificate.

**With Docker**

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir streamlit pandas numpy scikit-learn twilio python-dotenv supabase
EXPOSE 8501
ENTRYPOINT ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.headless=true"]
```

Then build and run:

```bash
docker build -t queue-dashboard .
docker run -d -p 8501:8501 --env-file .env queue-dashboard
```


## Troubleshooting

**ESP32 won't connect to Wi-Fi** — Double check the SSID and password in `config.h`. The ESP32 only works with 2.4 GHz networks, not 5 GHz.

**Data not showing up in Supabase** — Make sure the URL and API key are correct. Check that the Row Level Security policies allow inserts from the `anon` role.

**Sensor readings are jumpy** — Check your wiring. Use `INPUT_PULLUP` mode and add a small debounce delay (around 200ms) in the firmware.

**Python module not found errors** — Make sure your virtual environment is activated and you've installed all the dependencies.

**`queue_data.csv` not found** — You need to be in the `ml/` directory when running `train_model.py`, or change the script to use an absolute path.

**Supabase returns 401 or 403** — The API key is wrong, expired, or the RLS policies aren't set up. Regenerate the key from the Supabase dashboard and double check the policies.

**WhatsApp message not arriving** — Make sure you've joined the Twilio sandbox by sending the join code from your phone. Sandbox sessions expire, so you might need to rejoin.

**Streamlit won't start** — Check that it's installed (`pip install streamlit`) and that port 8501 isn't being used by something else. You can change the port with `--server.port 8502`.

**Supabase project is paused** — Free tier projects get paused after a period of inactivity. Go to the Supabase dashboard and unpause it.
