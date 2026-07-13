import os
import numpy as np
import pandas as pd 
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import streamlit as st

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

st.title("Smart Queue Prediction System")

queue_count = st.slider("Queue Count", 0, 250, 20)

avg_service_time = st.slider(
    "Average Service Time",
    1.0,
    20.0,
    5.0
)

active_counters = st.slider(
    "Active Counters",
    1,
    8,
    3
)

hour_of_day = st.slider(
    "Hour of Day",
    9,
    17,
    11
)

day_of_week = st.slider(
    "Day of Week",
    0,
    6,
    0
)


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
st.success(
    f"Predicted Wait Time: {prediction[0]:.2f} minutes"
)