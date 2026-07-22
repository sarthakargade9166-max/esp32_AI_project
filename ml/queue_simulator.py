import csv
import os
import random
import time
from datetime import datetime

# Simulation mode: 'realtime' for demo, 'accelerated' for fast training data creation
SIMULATION_MODE = 'realtime'

# Path to dataset file
csv_path = os.path.join(os.path.dirname(__file__), 'queue_data.csv')

# Traffic configuration (arrival chance and delay in seconds)
traffic_config = {
    'heavy': {'enter_chance': 0.80, 'delay': (1, 2)},
    'moderate': {'enter_chance': 0.70, 'delay': (2, 4)},
    'low': {'enter_chance': 0.60, 'delay': (4, 7)},
    'decreasing': {'enter_chance': 0.40, 'delay': (3, 6)},
    'off_peak': {'enter_chance': 0.55, 'delay': (5, 8)}
}

# Fast delay for accelerated mode (in seconds)
accelerated_delay = (0.01, 0.05)


# Read existing CSV file to restore event_id and current people_inside
def load_previous_state():
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        return 1, 0

    last_id = 0
    people_inside = 0

    with open(csv_path, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if 'event_id' in row and row['event_id'].isdigit():
                last_id = max(last_id, int(row['event_id']))

            event_type = row.get('event_type', '').upper()
            if event_type == 'ENTER':
                people_inside += 1
            elif event_type == 'EXIT':
                people_inside = max(0, people_inside - 1)

    return last_id + 1, people_inside


# Check traffic level based on hour of the day
def get_traffic_level():
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


# Generate an ENTER or EXIT event based on traffic and people inside
def generate_event(people_inside):
    traffic = get_traffic_level()
    base_chance = traffic_config[traffic]['enter_chance']

    # Nobody inside, so next person must enter
    if people_inside <= 0:
        event_type = 'ENTER'
    else:
        if people_inside < 15:
            enter_chance = max(base_chance, 0.65)
        elif people_inside < 35:
            enter_chance = base_chance
        else:
            enter_chance = max(0.1, base_chance - 0.25)

        if random.random() < enter_chance:
            event_type = 'ENTER'
        else:
            event_type = 'EXIT'

    # Update count of people inside
    if event_type == 'ENTER':
        people_inside += 1
    else:
        people_inside = max(0, people_inside - 1)

    return event_type, people_inside, traffic


# Calculate sleep delay based on mode and traffic
def get_event_delay(traffic):
    if SIMULATION_MODE == 'accelerated':
        min_delay, max_delay = accelerated_delay
    else:
        min_delay, max_delay = traffic_config[traffic]['delay']

    return random.uniform(min_delay, max_delay)


# Save a single event to CSV (can be swapped with Supabase database later)
def write_event(event_id, timestamp, event_type):
    file_exists = os.path.exists(csv_path)

    with open(csv_path, mode='a', newline='') as file:
        writer = csv.writer(file)

        # Write header if file is new
        if not file_exists or os.path.getsize(csv_path) == 0:
            writer.writerow(['event_id', 'timestamp', 'event_type'])

        writer.writerow([event_id, timestamp, event_type])


# Run the main simulator loop
def run_simulator():
    event_id, people_inside = load_previous_state()

    print('Starting Queue Simulator...')
    print('Mode:', SIMULATION_MODE)
    print('Resuming event_id from:', event_id)
    print('Resuming people_inside from:', people_inside)
    print('Press Ctrl+C to stop.\n')

    try:
        while True:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            display_time = datetime.now().strftime('%H:%M:%S')

            event_type, people_inside, traffic = generate_event(people_inside)

            write_event(event_id, timestamp, event_type)

            print(f'[{display_time}]')
            print(f'Traffic: {traffic.capitalize()}')
            print(f'Event: {event_type}')
            print(f'People Inside: {people_inside}')
            print('-' * 25)

            delay = get_event_delay(traffic)
            time.sleep(delay)

            event_id += 1

    except KeyboardInterrupt:
        print('\nSimulator stopped.')


if __name__ == '__main__':
    run_simulator()
