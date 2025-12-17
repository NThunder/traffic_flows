import csv
from datetime import datetime
import os
from tqdm import tqdm

def convert_time(time_str):
    """Преобразование времени из GTFS формата"""
    hours_converted = int(time_str[:2]) % 24
    return "{:02d}:".format(hours_converted) + time_str[3:]

def parse_gtfs_limited(directory, limit=100):
    """Парсинг GTFS данных с ограничением количества записей"""
    # Read files
    stops_path = os.path.join(directory, 'stops.txt')
    stop_times_path = os.path.join(directory, 'stop_times.txt')
    trips_path = os.path.join(directory, 'trips.txt')
    routes_path = os.path.join(directory, 'routes.txt')
    calendar_path = os.path.join(directory, 'calendar.txt')

    # Read stops (first 10000)
    all_stops = set()
    with open(stops_path, 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(tqdm(reader, desc="Reading stops", total=min(limit, 10105))):
            if i >= limit:
                break
            all_stops.add(row['stop_id'])

    # Read routes, trips, calendar to determine active services (for Dec 17, 2025 - Wednesday)
    # Assume start_date, end_date in YYYYMMDD, wednesday=1
    active_services = set()
    date_str = '20251217'  # YYYYMMDD for Dec 17, 2025
    weekday = 'wednesday'
    with open(calendar_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            start = row['start_date']
            end = row['end_date']
            if start <= date_str <= end and row[weekday] == '1':
                active_services.add(row['service_id'])

    # Filter trips by active services
    active_trips = {}
    with open(trips_path, 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(tqdm(reader, desc="Reading trips", total=min(limit, 25000))):
            if i >= limit:
                break
            if row['service_id'] in active_services:
                active_trips[row['trip_id']] = row['route_id']

    # Read stop_times, build links (first 10000)
    stop_times = {}
    with open(stop_times_path, 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(tqdm(reader, desc="Reading stop_times", total=min(limit, 2660216))):
            if i >= limit:
                break
            trip_id = row['trip_id']
            if trip_id not in active_trips:
                continue
            if trip_id not in stop_times:
                stop_times[trip_id] = []
            stop_times[trip_id].append(row)

    return stop_times, active_trips, all_stops

def calculate_headways(stop_times, active_trips):
    """Расчет интервалов движения"""
    from datetime import datetime
    from collections import defaultdict
    
    # Calculate headways: For each route, stop, collect departure times, sort, avg diff
    departures = {}  # (route_id, stop_id) -> list of dep_times in seconds
    for trip_id, times in tqdm(stop_times.items(), desc="Processing trips for headways"):
        route_id = active_trips[trip_id]
        for st in times:
            stop_id = st['stop_id']
            key = (route_id, stop_id)
            if key not in departures:
                departures[key] = []
            dep_time = datetime.strptime(convert_time(st['departure_time']), '%H:%M:%S')
            seconds = dep_time.hour * 3600 + dep_time.minute * 60 + dep_time.second
            departures[key].append(seconds)

    for key in tqdm(departures.keys(), desc="Calculating headways"):
        deps = sorted(departures[key])
        if len(deps) > 1:
            diffs = [deps[i+1] - deps[i] for i in range(len(deps)-1)]
            avg_headway = sum(diffs) / len(diffs) / 60.0  # minutes
            departures[key] = avg_headway
        else:
            departures[key] = 0.0  # or infinite

    return departures