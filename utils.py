import csv
from datetime import datetime
import heapq
import os
from tqdm import tqdm
import random
random.seed(42)

ALPHA = 1.0
INFINITE_FREQUENCY = 99999999999.0
MATH_INF = float('inf')
VERBOSE = False
EPSILON = 1e-6

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

class PriorityQueue:
    def __init__(self):
        self.heap = []
        self.entry_finder = {}
        self.counter = 0

    def push(self, link, priority):
        key = (link.from_node, link.to_node, link.route_id)
        if key in self.entry_finder:
            self._remove_entry(key)
        count = self.counter
        self.counter += 1
        entry = [priority, count, link]
        self.entry_finder[key] = entry
        heapq.heappush(self.heap, entry)

    def _remove_entry(self, key):
        entry = self.entry_finder.pop(key)
        entry[-1] = 'REMOVED'

    def pop(self):
        while self.heap:
            priority, count, link = heapq.heappop(self.heap)
            if link != 'REMOVED':
                key = (link.from_node, link.to_node, link.route_id)
                del self.entry_finder[key]
                return link, priority
        return None, None

    def update(self, link, priority):
        self.push(link, priority)
        
class PriorityQueue2:
    def __init__(self):
        self.heap = []
        self.entry_finder = {}
        self.counter = 0

    def push(self, link, priority1, priority2):
        key = (link.from_node, link.to_node, link.route_id)
        if key in self.entry_finder:
            self._remove_entry(key)
        count = self.counter
        self.counter += 1
        entry = [priority1, priority2, count, link]
        self.entry_finder[key] = entry
        heapq.heappush(self.heap, entry)

    def _remove_entry(self, key):
        entry = self.entry_finder.pop(key)
        entry[-1] = 'REMOVED'

    def pop(self):
        while self.heap:
            priority1, priority2, count, link = heapq.heappop(self.heap)
            if link != 'REMOVED':
                key = (link.from_node, link.to_node, link.route_id)
                del self.entry_finder[key]
                return link, priority1, priority2
        return None, None, None

    def update(self, link, priority1, priority2):
        self.push(link, priority1, priority2)

def convert_time(time_str):
    hours_converted = int(time_str[:2]) % 24
    return "{:02d}:".format(hours_converted) + time_str[3:]

def parse_gtfs_limited(directory, limit=100):
    stops_path = os.path.join(directory, 'stops.txt')
    stop_times_path = os.path.join(directory, 'stop_times.txt')
    trips_path = os.path.join(directory, 'trips.txt')
    routes_path = os.path.join(directory, 'routes.txt')
    calendar_path = os.path.join(directory, 'calendar.txt')

    all_stops = set()
    stop_names = {}  # Словарь для хранения названий остановок
    with open(stops_path, 'r', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(tqdm(reader, desc="Reading stops", total=min(limit, 10105))):
            all_stops.add(row['stop_id'])
            stop_names[row['stop_id']] = row.get('stop_name', row['stop_id'])  # Используем ID, если название отсутствует
            if i == 0 or i == 10:
                print(row['stop_id'])

    # Загружаем названия маршрутов
    route_names = {}
    with open(routes_path, 'r', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in tqdm(reader, desc="Reading routes"):
            # Формируем название маршрута: сначала краткое (номер), потом полное
            short_name = row.get('route_short_name', '')
            long_name = row.get('route_long_name', '')
            
            if short_name and long_name:
                route_names[row['route_id']] = f"{short_name} - {long_name}"
            elif short_name:
                route_names[row['route_id']] = short_name
            elif long_name:
                route_names[row['route_id']] = long_name
            else:
                route_names[row['route_id']] = row['route_id']

    active_services = set()
    date_str = '20251217'  # Dec 17, 2025
    weekday = 'wednesday'
    with open(calendar_path, 'r', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            start = row['start_date']
            end = row['end_date']
            if start <= date_str <= end and row[weekday] == '1':
                active_services.add(row['service_id'])

    active_trips = {}
    with open(trips_path, 'r', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(tqdm(reader, desc="Reading trips", total=min(limit, 25000))):
            if row['service_id'] in active_services:
                active_trips[row['trip_id']] = row['route_id']

    stop_times = {}
    with open(stop_times_path, 'r', encoding="utf-8") as f:
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

    return stop_times, active_trips, all_stops, stop_names, route_names

def calculate_links(stop_times, active_trips, all_stops):
    all_links = []
    for trip_id, times in tqdm(stop_times.items(), desc="Creating links"):
        times.sort(key=lambda x: int(x['stop_sequence']))
        route_id = active_trips[trip_id]
        for idx in range(len(times) - 1):
            current = times[idx]
            next_stop = times[idx + 1]
            from_node = current['stop_id']
            to_node = next_stop['stop_id']
            
            if from_node not in all_stops or to_node not in all_stops:
                continue
                
            dep_time = datetime.strptime(convert_time(current['departure_time']), '%H:%M:%S')
            arr_time = datetime.strptime(convert_time(next_stop['arrival_time']), '%H:%M:%S')
            mean_travel_time = (arr_time - dep_time).total_seconds() / 60.0 # minutes

            headway = 0.0 # sets actual headway later

            link = Link(from_node, to_node, route_id, mean_travel_time, headway)
            all_links.append(link)

    return all_links

def calculate_headways(stop_times, active_trips, all_links):
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
            avg_headway = sum(diffs) / len(diffs) / 60.0 # minutes
            departures[key] = avg_headway
        else:
            departures[key] = 0.0

    for link in tqdm(all_links, desc="Assigning headways"):
        key = (link.route_id, link.from_node)
        link.headway = departures.get(key, 0.0)

    return all_links

def find_shortest_route_pair(all_links, max_stops=10):
    """
    Находит пару остановок с маршрутом длиной не более max_stops остановок
    """
    from collections import defaultdict, deque
    
    # Построим граф
    graph = defaultdict(list)
    nodes = set()
    for link in all_links:
        graph[link.from_node].append(link.to_node)
        nodes.add(link.from_node)
        nodes.add(link.to_node)
    
    if len(nodes) < 2:
        return None, None

    node_list = list(nodes)
    
    # Попробуем найти кратчайший маршрут между парами узлов
    for origin in node_list[:100]:  # Ограничиваем количество проверяемых origin
        # Используем BFS для поиска ближайших узлов
        visited = {origin: 0}
        queue = deque([(origin, 0)])
        
        while queue:
            current, dist = queue.popleft()
            
            if dist > 0 and dist <= max_stops and current != origin:
                # Проверим, что между origin и current есть путь (а не только расстояние по BFS)
                # Проверим, что у нас есть связный маршрут
                path_exists = True  # Упрощаем проверку, т.к. BFS уже нашел путь
                if path_exists:
                    return origin, current
            
            if dist >= max_stops:
                continue
                
            for neighbor in graph[current]:
                if neighbor not in visited:
                    visited[neighbor] = dist + 1
                    queue.append((neighbor, dist + 1))
    
    return None, None

from collections import defaultdict, deque

def find_connected_od_pair_with_min_hops(all_links, min_hops=10, max_total_nodes=10000):
    """
    Находит первую пару (origin, destination), для которой кратчайший путь
    содержит хотя бы `min_hops` рёбер.
    """
    graph = defaultdict(list)
    nodes = set()
    for link in all_links:
        graph[link.from_node].append(link.to_node)
        nodes.add(link.from_node)
        nodes.add(link.to_node)

    if len(nodes) < 2:
        return None, None

    node_list = list(nodes)
    total_checked = 0

    for origin in node_list:
        dist = {origin: 0}
        queue = deque([origin])
        
        while queue:
            current = queue.popleft()
            current_dist = dist[current]
            
            if current_dist >= min_hops and current != origin:
                return origin, current

            if current_dist >= min_hops + 5:
                continue

            for neighbor in graph[current]:
                if neighbor not in dist:
                    dist[neighbor] = current_dist + 1
                    queue.append(neighbor)

        total_checked += 1
        if total_checked > max_total_nodes:
            break

    return None, None


def get_all_origins_reaching_destination(all_links, destination):
    """
    Строит обратный граф и находит все узлы, из которых можно добраться до destination.
    """
    rev_graph = defaultdict(list)
    all_nodes = set()
    for link in all_links:
        rev_graph[link.to_node].append(link.from_node)
        all_nodes.add(link.from_node)
        all_nodes.add(link.to_node)

    reachable = set()
    queue = deque([destination])
    reachable.add(destination)

    while queue:
        current = queue.popleft()
        for predecessor in rev_graph[current]:
            if predecessor not in reachable:
                reachable.add(predecessor)
                queue.append(predecessor)

    return reachable

def calculate_flow_volumes(all_links, all_stops, optimal_strategy, od_matrix, destination):
    node_volumes = {stop: 0.0 for stop in all_stops}
    for origin in od_matrix:
        if destination in od_matrix[origin]:
            node_volumes[origin] += od_matrix[origin][destination]
            # node_volumes[destination] += od_matrix[origin][destination]
    # node_volumes[destination] *= -1

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
            if node_volumes[k] != 0.0:
                print(f"  V_{k} = {node_volumes[k]}")

    return Volumes(volumes_links, node_volumes)

def compute_average_volume(volumes):
    total_volume = 0.0
    count = 0

    for from_node in volumes.links:
        for to_node in volumes.links[from_node]:
            v = volumes.links[from_node][to_node]
            if v != 0:
                total_volume += v
                count += 1

    avg_volume = total_volume / count if count > 0 else 0.0
    return avg_volume, total_volume, count

import os
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D

def visualize_volumes(all_links, all_stops, volumes_orig, volumes_mod,
                      od_matrix, destination, T=60, visualization_dir="visual"):
    os.makedirs(visualization_dir, exist_ok=True)

    G = nx.DiGraph()

    link_attributes = {}
    for link in all_links:
        G.add_edge(link.from_node, link.to_node)
        link_attributes[(link.from_node, link.to_node)] = {
            'headway': link.headway,
            'travel_cost': link.travel_cost,
            'route_id': link.route_id
        }

    origins = set()
    for orig, dest_dict in od_matrix.items():
        if destination in dest_dict and dest_dict[destination] > 0:
            origins.add(orig)

    plt.figure(figsize=(16, 12))
    pos = nx.spring_layout(G, seed=42, k=0.9, iterations=60)

    node_colors = []
    for node in G.nodes():
        if node == destination:
            node_colors.append('red')
        elif node in origins:
            node_colors.append('limegreen')
        else:
            node_colors.append('lightblue')

    nx.draw_networkx_nodes(G, pos,
                           node_color=node_colors,
                           node_size=1000,
                           alpha=0.9,
                           linewidths=2,
                           edgecolors='black')

    nx.draw_networkx_edges(G, pos,
                           edge_color='gray',
                           arrows=True,
                           arrowsize=25,
                           width=2,
                           alpha=0.7)

    intermediate_nodes = [node for node in G.nodes() if node != destination and node not in origins]
    if intermediate_nodes:
        nx.draw_networkx_labels(G, pos,
                                labels={node: node for node in intermediate_nodes},
                                font_size=11,
                                font_weight='bold',
                                font_color='black')

    if origins:
        nx.draw_networkx_labels(G, pos,
                                labels={node: node for node in origins},
                                font_size=11,
                                font_weight='bold',
                                font_color='white')

    nx.draw_networkx_labels(G, pos,
                            labels={destination: destination},
                            font_size=11,
                            font_weight='bold',
                            font_color='white')

    edge_labels_volumes = {}
    for from_node in volumes_orig.links:
        for to_node in volumes_orig.links[from_node]:
            v_orig = volumes_orig.links[from_node][to_node]
            v_mod = volumes_mod.links.get(from_node, {}).get(to_node, 0.0)
            if v_orig > 0.01 or v_mod > 0.01:
                edge_labels_volumes[(from_node, to_node)] = f"orig: {v_orig:.1f}\nmod: {v_mod:.1f}"

    edge_labels_attributes = {}
    for (from_node, to_node) in G.edges():
        if (from_node, to_node) in link_attributes:
            attrs = link_attributes[(from_node, to_node)]
            headway = attrs['headway']
            travel_cost = attrs['travel_cost']
            
            if headway < 0:
                headway_str = "Inf"
            else:
                headway_str = f"{headway:.1f}"
            
            edge_labels_attributes[(from_node, to_node)] = f"h: {headway_str}\nt: {travel_cost:.1f}m"

    nx.draw_networkx_edge_labels(G, pos,
                                 edge_labels=edge_labels_volumes,
                                 font_size=9,
                                 font_color='darkred',
                                 bbox=dict(facecolor='white', edgecolor='none', alpha=0.8, pad=3))

    pos_offset = {}
    for node, (x, y) in pos.items():
        pos_offset[node] = (x - 0.08, y - 0.08)

    nx.draw_networkx_edge_labels(G, pos_offset,
                                 edge_labels=edge_labels_attributes,
                                 font_size=7,
                                 font_color='darkblue',
                                 bbox=dict(facecolor='lightyellow', edgecolor='none', alpha=0.7, pad=2))

    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Пункт назначения',
               markerfacecolor='red', markersize=12, markeredgecolor='black'),
        Line2D([0], [0], marker='o', color='w', label='Стартовая зона (origin)',
               markerfacecolor='limegreen', markersize=12, markeredgecolor='black'),
        Line2D([0], [0], marker='o', color='w', label='Промежуточная остановка',
               markerfacecolor='lightblue', markersize=12, markeredgecolor='black'),
    ]
    plt.legend(handles=legend_elements, loc='upper left', fontsize=12, framealpha=0.9)

    plt.title(f"Сравнение пассажиропотоков: Original vs Modified модель\n"
              f"Destination = {destination} | Deadline T = {T} мин\n"
              f"Красные подписи: объёмы потоков | Синие подписи: h=headway, t=travel_time (мин)",
              fontsize=12, pad=30)

    plt.axis('off')
    plt.tight_layout()

    filename = os.path.join(visualization_dir, "network_volumes_highlighted.png")
    plt.savefig(filename, dpi=200, bbox_inches='tight')
    plt.close()

    print(f"График успешно сохранён: {filename}")