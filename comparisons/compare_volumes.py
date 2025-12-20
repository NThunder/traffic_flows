
from algos.florian import find_optimal_strategy, assign_demand as assign_demand_florain, parse_gtfs
from algos.time_arrived_florian import find_optimal_strategy as  find_optimal_strategy_modified, assign_demand as assign_demand_time_arrived
from utils import *
import networkx as nx
import matplotlib.pyplot as plt
import os

def parse_sample_data():
    all_stops = {
        'Res1', 'Res2', 'Res3',
        'Metro_North', 'Metro_Center',
        'Downtown', 'University',
        'Mid1', 'Mid3', 'Mid4'
    }

    links_data = [
        # Надёжный метро путь: низкая variance
        ('Res1', 'Metro_North', 'M1', 10, 2, 5),  # mean=10, std=2 (low risk)
        ('Metro_North', 'Metro_Center', 'M1', 15, 2, 5),
        ('Metro_Center', 'Downtown', 'M1', 10, 2, 5),

        # Рискованный быстрый автобус: высокая variance
        ('Res1', 'Mid1', 'B1', 8, 15, 10),  # mean=8, std=15 (high risk)
        ('Mid1', 'Downtown', 'B1', 12, 15, 10),

        # Для Res2: путь к University
        ('Res2', 'University', 'U1', 20, 3, 8),  # moderate

        # Для Res3: рискованный прямой
        ('Res3', 'Downtown', 'X2', 15, 20, 20),  # fast mean=15, high std=20

        # Надёжный альтернативный для Res3 через метро
        ('Res3', 'Metro_Center', 'M2', 18, 2, 5),
        # Используем существующий Metro_Center -> Downtown

        # Другие линки для связности
        ('University', 'Mid3', 'U2', 5, 2, 8),
        ('Mid3', 'Metro_Center', 'U2', 10, 2, 8),

        ('Metro_Center', 'Mid4', 'C1', 5, 10, 15),  # mixed
        ('Mid4', 'Downtown', 'C1', 6, 10, 15),

        ('Downtown', 'University', 'C2', 7, 5, 15),
        ('University', 'Metro_Center', 'C2', 8, 5, 15),

        ('Metro_Center', 'Downtown', 'WALK', 12, 0, 0),

        ('Res2', 'Downtown', 'R1', 25, 10, 30),
        ('Downtown', 'Res2', 'R1', 25, 10, 30),
    ]

    unique_links = {}
    for from_node, to_node, route_id, mean_time, std_time, headway in links_data:
        key = (from_node, to_node, route_id)
        if key not in unique_links:
            unique_links[key] = {
                'mean_time': [],
                'std_time': [],
                'headway': headway
            }
        unique_links[key]['mean_time'].append(mean_time)
        unique_links[key]['std_time'].append(std_time)
    
    all_links = []
    for (from_node, to_node, route_id), data in unique_links.items():
        mean_time = sum(data['mean_time']) / len(data['mean_time'])
        std_time = sum(data['std_time']) / len(data['std_time'])
        headway = data['headway']
        link = Link(from_node=from_node, to_node=to_node, route_id=route_id, travel_cost=mean_time, headway=headway, mean_travel_time=mean_time, std_travel_time=std_time)
        all_links.append(link)
    
    return all_links, all_stops


def compare_approaches(T=60):
    directory = "improved-gtfs-moscow-official"
    all_links, all_stops = parse_gtfs(directory, 100000)

    print("🔍 Ищем пару связанных остановок...")
    origin, destination = find_connected_od_pair_with_min_hops(all_links)

    if origin is None or destination is None:
        raise ValueError("Не удалось найти ни одной пары остановок с путём между ними!")

    print(f"✅ Найдена пара: origin={origin}, destination={destination}")

    origins_reaching_dest = get_all_origins_reaching_destination(all_links, destination)

    print(f"🎯 Найдено {len(origins_reaching_dest)} остановок, из которых можно доехать до {destination}")

    od_matrix = {}
    for origin in origins_reaching_dest:
        if origin != destination:
            demand = random.uniform(50.0, 500.0)
            od_matrix[origin] = {destination: demand}

    print(f"📊 OD-матрица создана: {len(od_matrix)} origin → {destination} (случайный спрос)")
    # result = compute_sf(all_links, all_stops, destination, od_matrix)    
    
    
    
    
    # all_links, all_stops = parse_sample_data()
    strategy_orig = find_optimal_strategy(all_links, all_stops, destination)
    volumes_orig = assign_demand_florain(all_links, all_stops, strategy_orig, od_matrix, destination)
    strategy_mod = find_optimal_strategy_modified(all_links, all_stops, destination, T)
    volumes_mod = assign_demand_time_arrived(all_links, all_stops, strategy_mod, od_matrix, destination)
    
    avg_orig_A, total_orig_A, count_orig_A = compute_average_volume(volumes_orig)
    avg_mod_A, total_mod_A, count_mod_A = compute_average_volume(volumes_mod)
    
    print("Сравнение распределений потоков (original vs modified):")
    for from_node in volumes_orig.links:
        for to_node in volumes_orig.links[from_node]:
            v_orig = volumes_orig.links[from_node][to_node]
            v_mod = volumes_mod.links.get(from_node, {}).get(to_node, 0.0)
            print(f"Link ({from_node} -> {to_node}): orig={v_orig}, mod={v_mod}, diff={v_mod - v_orig}")

    # Вывод
    print("\n📊 Средний объём на рёбрах:")
    print(f"Original (только активные):  среднее = {avg_orig_A:.2f}, всего рёбер = {count_orig_A}", total_orig_A)
    print(f"Modified (только активные): среднее = {avg_mod_A:.2f}, всего рёбер = {count_mod_A}", total_mod_A)

    print(f"Изменение среднего (активные): {avg_mod_A - avg_orig_A:+.2f}")
        
# compare_approaches(60)

def compare_fix_approaches(od_matrix, destination, T=60):
    all_links, all_stops = parse_sample_data()
    strategy_orig = find_optimal_strategy(all_links, all_stops, destination)
    volumes_orig = assign_demand_florain(all_links, all_stops, strategy_orig, od_matrix, destination)
    strategy_mod = find_optimal_strategy_modified(all_links, all_stops, destination, T)
    volumes_mod = assign_demand_time_arrived(all_links, all_stops, strategy_mod, od_matrix, destination)
    print("Сравнение распределений потоков (original vs modified):")
    for from_node in volumes_orig.links:
        for to_node in volumes_orig.links[from_node]:
            v_orig = volumes_orig.links[from_node][to_node]
            v_mod = volumes_mod.links.get(from_node, {}).get(to_node, 0.0)
            print(f"Link ({from_node} -> {to_node}): orig={v_orig}, mod={v_mod}, diff={v_mod - v_orig}")

    visualize_volumes(all_links, all_stops, volumes_orig, volumes_mod, 
                        od_matrix, destination, T)

od_matrix = {
    'Res1': {
        'Downtown': 120,
    },
    'Res3': {
        'Downtown': 70,
    },
}
compare_fix_approaches(od_matrix, 'Downtown', 30)