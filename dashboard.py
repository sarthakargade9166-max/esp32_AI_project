import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Smart Queue Prediction System ~By Sarthak Argade",
    layout="wide"
)

page = st.sidebar.selectbox(
    "Select Page",
    [
        "Live Dashboard",
        "Today's Analytics",
        "Predictions & Insights"
    ]
)

# PAGE 1
if page == "Live Dashboard":

    st.title(" Smart Queue Monitoring System")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Current Queue", 15)

    with col2:
        st.metric("Average Service Time", "5 min")

    with col3:
        st.metric("Current Wait Estimate", "75 min")

    st.divider()

    st.subheader("Today's Status")

    col4, col5, col6 = st.columns(3)

    with col4:
        st.metric("People Entered", 120)

    with col5:
        st.metric("People Exited", 105)

    with col6:
        st.metric("WhatsApp Alerts", "Active")

# PAGE 2
elif page == "Today's Analytics":

    st.title(" Today's Analytics")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("People Served Today", 105)

        st.metric("Peak Hour", "11 AM - 1 PM")

        st.metric("Maximum Queue", 32)

    with col2:
        st.metric("Average Wait Time", "18 min")

        st.metric("Average Service Time", "5 min")

        st.metric("Total Visitors", 120)

# PAGE 3
elif page == "Predictions & Insights":

    st.title(" Predictions & Insights")

    st.metric("Busiest Day", "Monday")

    st.metric("Least Busy Day", "Thursday")

    st.metric("Best Time To Visit", "2 PM - 4 PM")

    st.metric("Predicted Crowd Tomorrow", "Medium")

    st.metric("Expected Wait Tomorrow", "10-20 min")

    st.success(
        "Recommendation: Visit Thursday between 2 PM and 4 PM."
    )