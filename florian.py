import heapq
import math
import csv
from datetime import datetime
import os
from tqdm import tqdm

class Link:
    def __init__(self, from_node, to_node, route_id, travel_cost, headway):
        self.from_node = from_node
        self.to_node = to_node
        self.route_id = route_id
        self.travel_cost = travel_cost
        self.headway = headway

class Strategy:
    def __init__(self, labels, freqs, a_set):
        self.labels = labels
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
        self.entry_finder = {}
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

def find_optimal_strategy(all_links, all_stops, destination):
    if VERBOSE:
        print("1.1 Initialization")
    u = {stop: 0.0 if stop == destination else MATH_INF for stop in all_stops}
    f = {stop: 0.0 for stop in all_stops}

    overline_a = []

    # Precompute links by ToNode
    links_by_to_node = {}
    for link in all_links:
        # Проверяем, что обе остановки существуют в all_stops
        if link.to_node in all_stops and link.from_node in all_stops:
            if link.to_node not in links_by_to_node:
                links_by_to_node[link.to_node] = []
            links_by_to_node[link.to_node].append(link)

    # Priority queue
    pq = PriorityQueue()
    for link in all_links:
        # Проверяем, что узел существует в all_stops
        if link.to_node in all_stops:
            pq.push(link, u[link.to_node] + link.travel_cost)

    while True:
        link, priority = pq.pop()
        if link is None or math.isinf(priority) or priority >= MATH_INF:
            break

        a = link
        i = a.from_node
        j = a.to_node
        
        # Проверяем, что обе остановки существуют в all_stops
        if i not in all_stops or j not in all_stops:
            continue
            
        sum_uc = u[j] + a.travel_cost

        if u[i] < sum_uc:
            continue

        if VERBOSE:
            print(f"Process: a = ({i}, {j})")
            print(f"  u_i < u_j + c_a : {u[i]} < {u[j]} + {a.travel_cost} - FALSE")

        freq = INFINITE_FREQUENCY if a.headway <= 0 else 1 / a.headway

        if VERBOSE:
            print(f"  f_a = {freq}")
            print(f"  u_j + c_a = {u[j] + a.travel_cost}")
            print(f"  u_i = {u[i]}")

        numerator_part = f[i] * u[i]
        if math.isnan(numerator_part):
            numerator_part = ALPHA
        numerator_part2 = freq * (u[j] + a.travel_cost)
        if math.isnan(numerator_part2):
            numerator_part2 = ALPHA
        numerator = numerator_part + numerator_part2
        denominator = f[i] + freq
        u[i] = numerator / denominator if denominator != 0 else ALPHA
        f[i] = denominator

        if VERBOSE:
            print(f"  u_i = {u[i]}")
            print(f"  f_i = {f[i]}")
            print(f"  overlineA += ({i}, {j})")

        overline_a.append(a)

        # Update PQ for links pointing to i (actually, links from nodes pointing to i? Wait, links that end at i are incoming, but update outgoing from predecessors)
        # In Go, it's linksByToNode[i] which are links ending at i, but then update entry for link.FromNode which is predecessor
        # Wait, in Go: linksToUpdate = linksByToNode[i]  # links ending at i
        # then for link in linksToUpdate:  # link is incoming to i
        # then iEntries = entries[link.FromNode]  # entries for from_node of incoming, i.e. predecessor
        # then for entry in iEntries:
        # if entry.link.ToNode == i and entry.link.FromNode == link.FromNode:  # entry for the incoming link
        # pq.update(entry, u[i] + link.TravelCost)  # update priority for the incoming link to u[i] + cost? No
        # Wait, link is incoming: from pred to i, cost is link.TravelCost for pred -> i
        # But priority for entry is u[ToNode] + TravelCost, ToNode is i, so u[i] + TravelCost? No
        # Wait, priority = u[j] + c_a where j = ToNode, a = (i,j)? No
        # In init: priority = u[link.ToNode] + link.TravelCost, for link (from, to), priority = u[to] + cost(from->to)
        # But in update, when u[i] updated, which links to update? Links that depend on u[i], i.e. links where ToNode == i? No
        # Wait, when u[i] changes, the priorities that use u[i] are for links where ToNode == i, priority = u[i] + c_a for a ending at i? No
        # Let's see: priority for a link a = (k, i), priority = u[i] + c_a where c_a is cost from k to i
        # Yes, so when u[i] changes, update priorities for links ending at i, i.e. incoming to i.
        # Yes, linksToUpdate = linksByToNode[i]  # ToNode == i, incoming
        # then for link in linksToUpdate: link = (pred, i)
        # then entry for that link, update to new u[i] + link.TravelCost
        # Yes.

        if i in links_by_to_node:
            for update_link in links_by_to_node[i]:  # update_link = (pred, i)
                # Проверяем существование узлов
                if update_link.to_node in all_stops and update_link.from_node in all_stops:
                    pq.update(update_link, u[i] + update_link.travel_cost)

        if VERBOSE:
            print("Node labels:")
            for s in all_stops:
                print(f"{s} -> (u_i, f_i) = ({u[s]}, {f[s]})")

    return Strategy(u, f, overline_a)

def assign_demand(all_links, all_stops, optimal_strategy, od_matrix, destination):
    # Sort a_set by descending (labels[to] + travel_cost)
    optimal_strategy.a_set = sorted(optimal_strategy.a_set, key=lambda a: -(optimal_strategy.labels[a.to_node] + a.travel_cost))

    node_volumes = {stop: 0.0 for stop in all_stops}
    for origin in od_matrix:
        if destination in od_matrix[origin]:
            node_volumes[origin] += od_matrix[origin][destination]
            node_volumes[destination] += od_matrix[origin][destination]
    node_volumes[destination] *= -1  # As in Go

    # Initialize volumes.links as dict[from][to] = 0
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

def compute_sf(all_links, all_stops, destination, od_matrix):
    ops = find_optimal_strategy(all_links, all_stops, destination)
    volumes = assign_demand(all_links, all_stops, ops, od_matrix, destination)
    return SFResult(ops, volumes)

def convert_time(time_str):
    hours_converted = int(time_str[:2]) % 24
    return "{:02d}:".format(hours_converted) + time_str[3:]

# GTFS Parsing
def parse_gtfs(directory, limit=10000):
    # Read files
    stops_path = os.path.join(directory, 'stops.txt')
    stop_times_path = os.path.join(directory, 'stop_times.txt')
    trips_path = os.path.join(directory, 'trips.txt')
    routes_path = os.path.join(directory, 'routes.txt')
    calendar_path = os.path.join(directory, 'calendar.txt')

    # Read stops
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

    # Read stop_times, build links
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

    all_links = []
    for trip_id, times in tqdm(stop_times.items(), desc="Creating links"):
        times.sort(key=lambda x: int(x['stop_sequence']))
        route_id = active_trips[trip_id]
        for idx in range(len(times) - 1):
            current = times[idx]
            next_stop = times[idx + 1]
            from_node = current['stop_id']
            to_node = next_stop['stop_id']
            
            # Проверяем, что обе остановки присутствуют в all_stops
            if from_node not in all_stops or to_node not in all_stops:
                continue
                
            # Parse times HH:MM:SS to minutes
            dep_time = datetime.strptime(convert_time(current['departure_time']), '%H:%M:%S')
            arr_time = datetime.strptime(convert_time(next_stop['arrival_time']), '%H:%M:%S')
            travel_cost = (arr_time - dep_time).total_seconds() / 60.0  # minutes

            # Headway: Need to calculate per route at from_node
            # For now, placeholder; in full, group departures per route/stop, compute avg headway
            headway = 0.0  # Set actual later

            link = Link(from_node, to_node, route_id, travel_cost, headway)
            all_links.append(link)

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

    # Assign headways to links (headway at from_node for route)
    for link in tqdm(all_links, desc="Assigning headways"):
        key = (link.route_id, link.from_node)
        link.headway = departures.get(key, 0.0)

    return all_links, all_stops

# Usage example (only when running as main script):
if __name__ == "__main__":
    directory = "improved-gtfs-moscow-official"
    all_links, all_stops = parse_gtfs(directory)
    od_matrix = { "100457-8017": { "100457-1002179": 1000 } }
    destination = "100457-1002179"
    result = compute_sf(all_links, all_stops, destination, od_matrix)