import heapq
import math
import csv
from datetime import datetime
import os
from scipy import stats  # Для нормального распределения в модификации

class Link:
    def __init__(self, from_node, to_node, route_id, travel_cost, headway, delay_mu=0, delay_sigma=5):
        self.from_node = from_node
        self.to_node = to_node
        self.route_id = route_id
        self.travel_cost = travel_cost
        self.headway = headway
        self.delay_mu = delay_mu
        self.delay_sigma = delay_sigma

class Strategy:
    def __init__(self, mean_var, freqs, a_set):
        self.mean_var = mean_var  # Вместо labels: dict[stop: (mean, var)]
        self.freqs = freqs
        self.a_set = a_set

class Volumes:
    def __init__(self, links, nodes):
        self.links = links
        self.nodes = nodes

class SFResult:
    def __init__(self, strategy, volumes):
        self.strategy = strategy
        self.volumes = volumes

ALPHA = 1.0
INFINITE_FREQUENCY = 99999999999.0
MATH_INF = float('inf')
VERBOSE = False

class PriorityQueue:
    def __init__(self):
        self.heap = []
        self.entry_finder = {}  # (from, to) -> [priority, count, link]
        self.counter = 0

    def push(self, link, priority):
        key = (link.from_node, link.to_node)
        if key in self.entry_finder:
            self._remove_entry(key)
        count = self.counter
        self.counter += 1
        entry = [priority, count, link]
        self.entry_finder[key] = entry
        heapq.heappush(self.heap, entry)

    def _remove_entry(self, key):
        entry = self.entry_finder.pop(key)
        entry[-1] = 'REMOVED'  # Mark as removed

    def pop(self):
        while self.heap:
            priority, count, link = heapq.heappop(self.heap)
            if link != 'REMOVED':
                key = (link.from_node, link.to_node)
                del self.entry_finder[key]
                return link, priority
        return None, None

    def update(self, link, priority):
        self.push(link, priority)  # Since push removes old if exists

def find_optimal_strategy(all_links, all_stops, destination, T=60):
    if VERBOSE:
        print("1.1 Initialization")
    # mean_var: dict[stop: (mean, var)] for remaining time ~ N(mean, sqrt(var))
    mean_var = {stop: (0.0, 0.0) if stop == destination else (MATH_INF, 0.0) for stop in all_stops}
    f = {stop: 0.0 for stop in all_stops}

    overline_a = []

    # Precompute links by ToNode
    links_by_to_node = {}
    for link in all_links:
        if link.to_node not in links_by_to_node:
            links_by_to_node[link.to_node] = []
        links_by_to_node[link.to_node].append(link)

    # Priority queue: Используем -R для max (min-heap как max-heap)
    pq = PriorityQueue()
    for link in all_links:
        # Initial priority: -P(on time) ≈ -(T - mean)/sqrt(var), но init с inf mean → low R
        pq.push(link, MATH_INF)  # Placeholder, update later

    while True:
        link, priority = pq.pop()
        if link is None or math.isinf(priority) or priority >= MATH_INF:
            break

        a = link
        i = a.from_node
        j = a.to_node

        # Compute current R_i = stats.norm.cdf(T - mean_var[i][0], 0, math.sqrt(mean_var[i][1]) if var>0 else inf)
        current_r = stats.norm.cdf(T - mean_var[i][0], scale=math.sqrt(mean_var[i][1]) if mean_var[i][1] > 0 else 0)

        # Wait approx: Для Exp, но Uniform(0, headway) для var
        freq = INFINITE_FREQUENCY if a.headway <= 0 else 1 / a.headway
        mean_wait = 0.5 / freq if freq < INFINITE_FREQUENCY else 0
        var_wait = (1/freq)**2 / 12 if freq < INFINITE_FREQUENCY else 0

        new_mean = mean_wait + a.travel_cost + a.delay_mu + mean_var[j][0]
        new_var = var_wait + a.delay_sigma**2 + mean_var[j][1]

        # Предполагаем улучшение если new_r > current_r, но для weighted
        # Compute tentative new_mean_var
        if f[i] == 0:
            tent_mean = new_mean
            tent_var = new_var
        else:
            total_f = f[i] + freq
            tent_mean = (f[i] * mean_var[i][0] + freq * new_mean) / total_f
            # Var for mixture approx
            tent_var = (f[i] * (mean_var[i][1] + mean_var[i][0]**2) + freq * (new_var + new_mean**2)) / total_f - tent_mean**2

        tent_r = stats.norm.cdf(T - tent_mean, scale=math.sqrt(tent_var) if tent_var > 0 else 0)

        if tent_r <= current_r:  # Не улучшает reliability
            continue

        # Update
        mean_var[i] = (tent_mean, tent_var)
        f[i] += freq
        overline_a.append(a)

        if VERBOSE:
            print(f"Process: a = ({i}, {j})")
            print(f"  Updated R_i = {tent_r}")

        # Update PQ: priority = -tent_r (для max)
        if i in links_by_to_node:
            for update_link in links_by_to_node[i]:
                # New priority for incoming: -R_i
                pq.update(update_link, -tent_r)

        if VERBOSE:
            print("Node mean_var:")
            for s in all_stops:
                print(f"{s} -> (mean, var) = {mean_var[s]}")

    return Strategy(mean_var, f, overline_a)

def assign_demand(all_links, all_stops, optimal_strategy, od_matrix, destination):
    # Sort a_set by descending expected time (proxy)
    optimal_strategy.a_set = sorted(optimal_strategy.a_set, key=lambda a: -(optimal_strategy.mean_var[a.to_node][0] + a.travel_cost))

    node_volumes = {stop: 0.0 for stop in all_stops}
    for origin in od_matrix:
        if destination in od_matrix[origin]:
            node_volumes[origin] += od_matrix[origin][destination]
            node_volumes[destination] += od_matrix[origin][destination]
    if destination in node_volumes:
        node_volumes[destination] *= -1

    volumes_links = {}
    for link in all_links:
        if link.from_node not in volumes_links:
            volumes_links[link.from_node] = {}
        volumes_links[link.from_node][link.to_node] = 0.0

    for a in optimal_strategy.a_set:
        freq = INFINITE_FREQUENCY if a.headway <= 0 else 1 / a.headway
        if optimal_strategy.freqs[a.from_node] == 0:
            va = 0.0
        else:
            va = (freq / optimal_strategy.freqs[a.from_node]) * node_volumes[a.from_node]
        if VERBOSE:
            print(f"Assigning demand for link: ({a.from_node}, {a.to_node})")
            print(f"  v_({a.from_node}, {a.to_node}) = {va}")
            print(f"  V_{a.to_node} += {va}")
        volumes_links[a.from_node][a.to_node] = va
        node_volumes[a.to_node] += va

    if VERBOSE:
        print("Final node volumes:")
        for k in node_volumes:
            print(f"  V_{k} = {node_volumes[k]}")

    return Volumes(volumes_links, node_volumes)

def compute_sf(all_links, all_stops, destination, od_matrix, T=60):
    ops = find_optimal_strategy(all_links, all_stops, destination, T)
    volumes = assign_demand(all_links, all_stops, ops, od_matrix, destination)
    return SFResult(ops, volumes)

def parse_gtfs(directory):
    stops_path = os.path.join(directory, 'stops.txt')
    stop_times_path = os.path.join(directory, 'stop_times.txt')
    trips_path = os.path.join(directory, 'trips.txt')
    routes_path = os.path.join(directory, 'routes.txt')
    calendar_path = os.path.join(directory, 'calendar.txt')

    all_stops = set()
    with open(stops_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_stops.add(row['stop_id'])

    active_services = set()
    date_str = '20251217'  # Dec 17, 2025
    weekday = 'wednesday'
    with open(calendar_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            start = row['start_date']
            end = row['end_date']
            if start <= date_str <= end and row[weekday] == '1':
                active_services.add(row['service_id'])

    active_trips = {}
    with open(trips_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['service_id'] in active_services:
                active_trips[row['trip_id']] = row['route_id']

    stop_times = {}
    with open(stop_times_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trip_id = row['trip_id']
            if trip_id not in active_trips:
                continue
            if trip_id not in stop_times:
                stop_times[trip_id] = []
            stop_times[trip_id].append(row)

    all_links = []
    for trip_id, times in stop_times.items():
        times.sort(key=lambda x: int(x['stop_sequence']))
        route_id = active_trips[trip_id]
        for idx in range(len(times) - 1):
            current = times[idx]
            next_stop = times[idx + 1]
            from_node = current['stop_id']
            to_node = next_stop['stop_id']
            dep_time = datetime.strptime(current['departure_time'], '%H:%M:%S')
            arr_time = datetime.strptime(next_stop['arrival_time'], '%H:%M:%S')
            travel_cost = (arr_time - dep_time).total_seconds() / 60.0

            headway = 0.0  # Placeholder

            link = Link(from_node, to_node, route_id, travel_cost, headway)
            all_links.append(link)

    departures = {}
    for trip_id, times in stop_times.items():
        route_id = active_trips[trip_id]
        for st in times:
            stop_id = st['stop_id']
            key = (route_id, stop_id)
            if key not in departures:
                departures[key] = []
            dep_time = datetime.strptime(st['departure_time'], '%H:%M:%S')
            seconds = dep_time.hour * 3600 + dep_time.minute * 60 + dep_time.second
            departures[key].append(seconds)

    for key in departures:
        deps = sorted(departures[key])
        if len(deps) > 1:
            diffs = [deps[i+1] - deps[i] for i in range(len(deps)-1)]
            avg_headway = sum(diffs) / len(diffs) / 60.0
            departures[key] = avg_headway
        else:
            departures[key] = 0.0

    for link in all_links:
        key = (link.route_id, link.from_node)
        link.headway = departures.get(key, 0.0)

    return all_links, all_stops

# Пример использования
# directory = 'path_to_gtfs_folder'
# all_links, all_stops = parse_gtfs(directory)
# od_matrix = {'origin_stop': {'destination_stop': 100.0}}  # Пример спроса
# destination = 'destination_stop'
# T = 60  # Deadline в минутах
# result = compute_sf(all_links, all_stops, destination, od_matrix, T)
# print(result.volumes.nodes)  # Пример вывода