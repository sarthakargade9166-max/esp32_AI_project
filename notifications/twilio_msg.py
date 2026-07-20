from twilio.rest import Client
from dotenv import load_dotenv
import os

load_dotenv()
 
def send_whatsapp_message(wait_time):
    client = Client(
        os.getenv("twilio_acc_sid"),
        os.getenv("twilio_auth_token")
    )

    message = client.messages.create(
        body="Waiting time is less than 5min for yor preffered queue",
        from_="whatsapp:+14155238886",
        to="whatsapp:+917219699787"
    )

    print(message.sid)
