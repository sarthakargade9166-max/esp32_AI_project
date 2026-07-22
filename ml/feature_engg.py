import os
import numpy as np
import pandas as pd

csv_path = os.path.join(os.path.dirname(__file__), 'queue_data.csv')
processed_csv_path = os.path.join(os.path.dirname(__file__), 'processed_features.csv')


def get_traffic_level(hour):
    if 8 <= hour < 9:
        return 1
    elif 9 <= hour < 11:
        return 3
    elif 11 <= hour < 13:
        return 2
    elif 13 <= hour < 14:
        return 1
    elif 14 <= hour < 17:
        return 3
    elif 17 <= hour < 18:
        return 4
    else:
        return 0


def load_data(file_path=csv_path):
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return pd.DataFrame()

    data = pd.read_csv(file_path)
    return data


def preprocess_data(data):
    if data.empty:
        return data

    df = data.copy()

    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

    if 'event_type' in df.columns:
        df['event_type'] = df['event_type'].astype(str).str.strip().str.upper()

    return df


def calculate_occupancy(df):
    if df.empty:
        df['current_occupancy'] = 0
        return df

    df = df.copy()

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


def calculate_hourly_features(df):
    if df.empty or 'timestamp' not in df.columns or 'event_type' not in df.columns:
        df['entries_last_hour'] = 0
        df['exits_last_hour'] = 0
        df['net_flow_last_hour'] = 0
        return df

    df = df.copy()

    dates = df['timestamp'].dt.date
    hours = df['timestamp'].dt.hour

    is_enter = (df['event_type'] == 'ENTER').astype(int)
    is_exit = (df['event_type'] == 'EXIT').astype(int)

    df['entries_last_hour'] = is_enter.groupby([dates, hours]).transform('sum')
    df['exits_last_hour'] = is_exit.groupby([dates, hours]).transform('sum')
    df['net_flow_last_hour'] = df['entries_last_hour'] - df['exits_last_hour']

    return df


def calculate_usage_statistics(df):
    if df.empty or 'timestamp' not in df.columns or 'event_type' not in df.columns:
        df['total_entries_today'] = 0
        df['total_exits_today'] = 0
        df['total_people_today'] = 0
        df['weekly_entries'] = 0
        df['weekly_exits'] = 0
        return df

    df = df.copy()
    dates = df['timestamp'].dt.date
    years = df['timestamp'].dt.year
    weeks = df['timestamp'].dt.isocalendar().week

    is_enter = (df['event_type'] == 'ENTER').astype(int)
    is_exit = (df['event_type'] == 'EXIT').astype(int)

    df['total_entries_today'] = is_enter.groupby(dates).cumsum()
    df['total_exits_today'] = is_exit.groupby(dates).cumsum()

    df['total_people_today'] = df['total_entries_today'] + df['total_exits_today']

    df['weekly_entries'] = is_enter.groupby([years, weeks]).transform('sum')
    df['weekly_exits'] = is_exit.groupby([years, weeks]).transform('sum')

    return df


def extract_time_features(df):
    if df.empty:
        return df

    df = df.copy()

    if 'timestamp' in df.columns:
        df['hour_of_day'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    else:
        if 'hour_of_day' not in df.columns:
            df['hour_of_day'] = 0
        if 'day_of_week' not in df.columns:
            df['day_of_week'] = 0
        if 'is_weekend' not in df.columns:
            df['is_weekend'] = 0

    traffic_list = []
    for hour in df['hour_of_day']:
        h = int(hour) if pd.notna(hour) else 0
        traffic_list.append(get_traffic_level(h))

    df['traffic_level'] = traffic_list
    return df


def build_feature_dataset(file_path=csv_path):
    raw_data = load_data(file_path)
    if raw_data.empty:
        return pd.DataFrame()

    df = preprocess_data(raw_data)
    df = calculate_occupancy(df)
    df = calculate_hourly_features(df)
    df = calculate_usage_statistics(df)
    df = extract_time_features(df)

    feature_columns = [
        'hour_of_day',
        'day_of_week',
        'is_weekend',
        'entries_last_hour',
        'exits_last_hour',
        'current_occupancy',
        'net_flow_last_hour',
        'total_people_today',
        'weekly_entries',
        'weekly_exits',
        'traffic_level',
    ]

    selected_columns = [col for col in feature_columns if col in df.columns]
    final_df = df[selected_columns].copy()

    return final_df


def save_feature_dataset(file_path=csv_path):
    df = build_feature_dataset(file_path)
    if not df.empty:
        df.to_csv(processed_csv_path, index=False)
        print('Processed features saved successfully.')
    else:
        print('No data available to save.')
    return df


def get_latest_features(file_path=csv_path):
    df = build_feature_dataset(file_path)
    if df.empty:
        return pd.DataFrame()

    return df.iloc[[-1]].reset_index(drop=True)


if __name__ == '__main__':
    features = save_feature_dataset()
    print('Features created successfully')
    print(f'Total rows: {len(features)}')

    latest = get_latest_features()
    print('\nLatest feature row:')
    print(latest)
