import os
import numpy as np
import pandas as pd

# Path to queue dataset file
csv_path = os.path.join(os.path.dirname(__file__), 'queue_data.csv')


# Read data from CSV file
def load_data(file_path=csv_path):
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return pd.DataFrame()

    data = pd.read_csv(file_path)
    return data


# Clean data and convert timestamp column
def preprocess_data(data):
    if data.empty:
        return data

    df = data.copy()

    # Convert timestamp column to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

    # Clean event_type text
    if 'event_type' in df.columns:
        df['event_type'] = df['event_type'].astype(str).str.strip().str.upper()

    return df


# Calculate current count of people inside
def calculate_occupancy(df):
    if df.empty:
        df['current_occupancy'] = 0
        return df

    df = df.copy()

    # Use existing column if present, else calculate running count
    if 'occupancy' in df.columns:
        df['current_occupancy'] = pd.to_numeric(df['occupancy'], errors='coerce').fillna(0).astype(int)
    elif 'queue_count' in df.columns:
        df['current_occupancy'] = pd.to_numeric(df['queue_count'], errors='coerce').fillna(0).astype(int)
    elif 'event_type' in df.columns:
        changes = []
        for event in df['event_type']:
            if event == 'ENTER':
                changes.append(1)
            elif event == 'EXIT':
                changes.append(-1)
            else:
                changes.append(0)

        running_total = np.cumsum(changes)
        df['current_occupancy'] = np.maximum(0, running_total)
    else:
        df['current_occupancy'] = 0

    return df


# Calculate entries, exits, and net flow in the last 1 hour
def calculate_hourly_features(df):
    if df.empty or 'timestamp' not in df.columns or 'event_type' not in df.columns:
        df['entries_last_hour'] = 0
        df['exits_last_hour'] = 0
        df['net_flow_last_hour'] = 0
        return df

    df = df.copy()

    # Mark entries and exits
    is_enter = (df['event_type'] == 'ENTER').astype(int)
    is_exit = (df['event_type'] == 'EXIT').astype(int)

    temp_df = pd.DataFrame({'enter': is_enter, 'exit': is_exit}, index=df['timestamp'])

    # Rolling 1 hour window sum
    entries_1h = temp_df['enter'].rolling('1h', closed='both').sum().fillna(0)
    exits_1h = temp_df['exit'].rolling('1h', closed='both').sum().fillna(0)

    df['entries_last_hour'] = entries_1h.values.astype(int)
    df['exits_last_hour'] = exits_1h.values.astype(int)
    df['net_flow_last_hour'] = df['entries_last_hour'] - df['exits_last_hour']

    return df


# Calculate total entries and exits for today
def calculate_daily_features(df):
    if df.empty or 'timestamp' not in df.columns or 'event_type' not in df.columns:
        df['total_entries_today'] = 0
        df['total_exits_today'] = 0
        return df

    df = df.copy()
    dates = df['timestamp'].dt.date

    is_enter = (df['event_type'] == 'ENTER').astype(int)
    is_exit = (df['event_type'] == 'EXIT').astype(int)

    df['total_entries_today'] = is_enter.groupby(dates).cumsum()
    df['total_exits_today'] = is_exit.groupby(dates).cumsum()

    return df


# Extract hour, day of week, and traffic level from timestamp
def extract_time_features(df):
    if df.empty:
        return df

    df = df.copy()

    if 'timestamp' in df.columns:
        df['hour_of_day'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['month'] = df['timestamp'].dt.month
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    else:
        if 'hour_of_day' not in df.columns:
            df['hour_of_day'] = 0
        if 'day_of_week' not in df.columns:
            df['day_of_week'] = 0
        if 'month' not in df.columns:
            df['month'] = 1
        if 'is_weekend' not in df.columns:
            df['is_weekend'] = 0

    # Determine traffic level by hour
    traffic_list = []
    for hour in df['hour_of_day']:
        if 8 <= hour < 9:
            traffic_list.append('low')
        elif 9 <= hour < 11:
            traffic_list.append('heavy')
        elif 11 <= hour < 13:
            traffic_list.append('moderate')
        elif 13 <= hour < 14:
            traffic_list.append('low')
        elif 14 <= hour < 17:
            traffic_list.append('heavy')
        elif 17 <= hour < 18:
            traffic_list.append('decreasing')
        else:
            traffic_list.append('off_peak')

    df['traffic_level'] = traffic_list
    return df


# Main function to build final ML feature dataset
def build_feature_dataset(file_path=csv_path):
    # Step 1: Read data
    raw_data = load_data(file_path)
    if raw_data.empty:
        return pd.DataFrame()

    # Step 2: Clean and extract features
    df = preprocess_data(raw_data)
    df = calculate_occupancy(df)
    df = calculate_hourly_features(df)
    df = calculate_daily_features(df)
    df = extract_time_features(df)

    # Step 3: Select columns for ML model
    feature_columns = [
        'timestamp',
        'hour_of_day',
        'day_of_week',
        'month',
        'is_weekend',
        'entries_last_hour',
        'exits_last_hour',
        'current_occupancy',
        'net_flow_last_hour',
        'traffic_level'
    ]

    selected_columns = [col for col in feature_columns if col in df.columns]
    final_df = df[selected_columns].copy()

    return final_df


if __name__ == '__main__':
    features = build_feature_dataset()
    print('Features created successfully:')
    print(f'Total rows: {len(features)}')
    if not features.empty:
        print(features.head())
