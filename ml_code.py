import os
import numpy as np
import pandas as pd 
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

df= pd.read_csv('queue_data.csv')
X = df[[
    "queue_count",
    "avg_service_time",
    "active_counters",
    "hour_of_day",
    "day_of_week"
]]
y= df["actual_wait"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = LinearRegression()  
model.fit(X_train, y_train)


new_data = pd.DataFrame({
    "queue_count": [100],
    "avg_service_time": [5.0],
    "active_counters": [1],
    "hour_of_day": [11],
    "day_of_week": [0]
})

##print("Actual wait:", model.predict(new_data))
#print(new_data)

prediction = model.predict(new_data)
 
if prediction[0] < 5:
    from twilio_msg import send_whatsapp_message
    send_whatsapp_message(prediction[0])

else:
    print("Waiting time is more than 5min for your preferred queue. No message sent.")