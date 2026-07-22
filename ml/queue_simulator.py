import csv
import os
import random
import time
from datetime import datetime

# Simulation Mode Configuration:
# - "realtime"    : Simulates real ESP32 hardware pace for live demonstrations.
# - "accelerated" : Fast event generation (0.01 - 0.05s delay) for dataset generation and ML training.
SIMULATION_MODE = "realtime"

# Storage configuration
CSV_PATH = os.path.join(os.path.dirname(__file__), 'queue_data.csv')

# Traffic level parameters (probabilities and real-time delay ranges in seconds)
TRAFFIC_CONFIG = {
    'heavy': {'enter_probability': 0.80, 'delay': (1, 2)},
    'moderate': {'enter_probability': 0.70, 'delay': (2, 4)},
    'low': {'enter_probability': 0.60, 'delay': (4, 7)},
    'decreasing': {'enter_probability': 0.40, 'delay': (3, 6)},
    'off_peak': {'enter_probability': 0.55, 'delay': (5, 8)}
}

# Delay range for accelerated mode (seconds)
ACCELERATED_DELAY = (0.01, 0.05)

# Occupancy thresholds
LOW_OCCUPANCY_THRESHOLD = 15
HIGH_OCCUPANCY_THRESHOLD = 35
MIN_ENTER_CHANCE_LOW_OCC = 0.65
HIGH_OCCUPANCY_PENALTY = 0.25


def load_initial_state(filepath=CSV_PATH):
    """
    Reads existing CSV file to restore event_id and calculate current occupancy.

    Returns:
        tuple: (next_event_id, current_occupancy)
    """
    if not os.path.isfile(filepath) or os.path.getsize(filepath) == 0:
        return 1, 0

    last_event_id = 0
    occupancy = 0

    with open(filepath, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                event_id_val = int(row.get('event_id', 0))
                if event_id_val > last_event_id:
                    last_event_id = event_id_val
            except ValueError:
                pass

            event_type = row.get('event_type', '').strip().upper()
            if event_type == 'ENTER':
                occupancy += 1
            elif event_type == 'EXIT':
                occupancy = max(0, occupancy - 1)

    return last_event_id + 1, occupancy


def get_current_traffic_level():
    """
    Determines traffic category based on current hour of the day.

    Returns:
        str: Key in TRAFFIC_CONFIG ('heavy', 'moderate', 'low', 'decreasing', 'off_peak')
    """
    hour = datetime.now().hour

    if 8 <= hour < 9:
        return 'low'
    elif 9 <= hour < 11:
        return 'heavy'
    elif 11 <= hour < 13:
        return 'moderate'
    elif 13 <= hour < 14:
        return 'low'
    elif 14 <= hour < 17:
        return 'heavy'
    elif 17 <= hour < 18:
        return 'decreasing'
    else:
        return 'off_peak'


def generate_event(occupancy):
    """
    Generates a raw ENTER or EXIT event based on traffic configuration and occupancy.

    Args:
        occupancy (int): Current count of people inside.

    Returns:
        tuple: (event_type, updated_occupancy, traffic_level)
    """
    traffic = get_current_traffic_level()
    config = TRAFFIC_CONFIG[traffic]
    base_enter = config['enter_probability']

    if occupancy <= 0:
        event_type = 'ENTER'
    else:
        if occupancy < LOW_OCCUPANCY_THRESHOLD:
            enter_chance = max(base_enter, MIN_ENTER_CHANCE_LOW_OCC)
        elif occupancy < HIGH_OCCUPANCY_THRESHOLD:
            enter_chance = base_enter
        else:
            enter_chance = max(0.1, base_enter - HIGH_OCCUPANCY_PENALTY)

        if random.random() < enter_chance:
            event_type = 'ENTER'
        else:
            event_type = 'EXIT'

    if event_type == 'ENTER':
        occupancy += 1
    else:
        occupancy = max(0, occupancy - 1)

    return event_type, occupancy, traffic


def calculate_event_delay(traffic, mode=SIMULATION_MODE):
    """
    Calculates sleep delay based on active SIMULATION_MODE and traffic level.

    Modes:
    - 'realtime'    : Uses traffic-specific realistic delay ranges (1-8s).
    - 'accelerated' : Uses fast delay range (0.01-0.05s) for bulk data generation.

    Args:
        traffic (str): Current traffic level key.
        mode (str): Active simulation mode name.

    Returns:
        float: Delay time in seconds.
    """
    if mode == "accelerated":
        min_d, max_d = ACCELERATED_DELAY
    else:
        min_d, max_d = TRAFFIC_CONFIG[traffic]['delay']

    return random.uniform(min_d, max_d)


def write_event(event_id, timestamp, event_type, filepath=CSV_PATH):
    """
    Appends a single event record to storage.

    NOTE: Replacing CSV with Supabase later requires modifying ONLY this function.

    Args:
        event_id (int): Incremental unique ID for the event.
        timestamp (str): Full datetime string.
        event_type (str): 'ENTER' or 'EXIT'.
        filepath (str): Destination CSV path.
    """
    file_exists = os.path.isfile(filepath)
    is_empty = not file_exists or os.path.getsize(filepath) == 0

    with open(filepath, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if is_empty:
            writer.writerow(['event_id', 'timestamp', 'event_type'])
        writer.writerow([event_id, timestamp, event_type])


def run_simulator():
    """
    Main loop running hardware simulator with dynamic delays based on SIMULATION_MODE.
    """
    event_id, occupancy = load_initial_state()

    print("==========================================")
    print("      Queue Hardware Simulator Started     ")
    print("==========================================")
    print(f"Simulation Mode: {SIMULATION_MODE.upper()}")
    print(f"Target file: {CSV_PATH}")
    print(f"Resuming from Event ID: {event_id}")
    print(f"Initial Occupancy: {occupancy}")
    print("Press Ctrl+C to stop simulation.\n")

    try:
        while True:
            now_full = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            now_time = datetime.now().strftime('%H:%M:%S')

            event_type, occupancy, traffic = generate_event(occupancy)

            write_event(event_id, now_full, event_type)

            print(f"[{now_time}]")
            print(f"Mode: {SIMULATION_MODE.capitalize()}")
            print(f"Traffic: {traffic.capitalize()}")
            print(f"Event: {event_type}")
            print(f"Occupancy: {occupancy}")
            print("-" * 25)

            delay = calculate_event_delay(traffic, SIMULATION_MODE)
            time.sleep(delay)

            event_id += 1

    except KeyboardInterrupt:
        print("\nSimulator stopped by user.")


if __name__ == '__main__':
    run_simulator()
