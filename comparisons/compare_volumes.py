
from algos.florian import find_optimal_strategy, assign_demand as assign_demand_florain, parse_gtfs
from algos.lateness_prob_florian import find_optimal_strategy as  find_optimal_strategy_modified, assign_demand as assign_demand_time_arrived
from utils import Link
import networkx as nx
import matplotlib.pyplot as plt
import os

def parse_sample_data():
    all_stops = {
        'Res1', 'Res2', 'Res3',
        'Metro_North', 'Metro_Center',
        'Downtown', 'University',
        'Mid1', 'Mid2', 'Mid3', 'Mid4'
    }

    links_data = [
        ('Res1', 'Metro_North', 'M1', 5, 1, 5), 
        ('Metro_North', 'Metro_Center', 'M1', 8, 1, 5),
        
        ('Res2', 'Mid1', 'B1', 6, 2, 10),
        
        ('Res3', 'Mid2', 'B2', 5, 3, 10),
        ('Mid2', 'University', 'B2', 10, 3, 10),
        
        ('Res2', 'Metro_Center', 'X1', 18, 4, 20),
        ('Res3', 'Downtown', 'X2', 22, 5, 20),
        
        ('University', 'Mid3', 'U1', 4, 2, 8),
        ('Mid3', 'Metro_Center', 'U1', 10, 2, 8),
        
        ('Metro_Center', 'Mid4', 'C1', 5, 2, 15),
        ('Mid4', 'Downtown', 'C1', 6, 2, 15),
        ('Downtown', 'University', 'C1', 7, 2, 15),
        ('University', 'Metro_Center', 'C1', 8, 2, 15),
        
        ('Metro_Center', 'Downtown', 'WALK', 12, 0, 0),
        ('University', 'Mid2', 'WALK', 4, 0, 0),
        

        ('Res1', 'Mid1', 'B3', 8, 2, 12),
        ('Mid1', 'Metro_Center', 'B3', 12, 2, 12),
        
        ('Res2', 'Downtown', 'R1', 25, 3, 30),
        ('Downtown', 'Res2', 'R1', 25, 3, 30),
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

def compare_approaches(od_matrix, destination, T=60):
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

    visualization_dir = "visualization"
    G = nx.DiGraph()
    
    for stop in all_stops:
        G.add_node(stop)
    
    for link in all_links:
        G.add_edge(link.from_node, link.to_node, weight=link.travel_cost, route=link.route_id)
    
    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(G)
    
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=1500, margins=0)
    
    nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20)
    
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
    
    edge_labels = {(link.from_node, link.to_node): f"{link.travel_cost}min\n({link.route_id})" 
                    for link in all_links}
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8)
    
    plt.title("Простая транспортная сеть для тестирования алгоритмов")
    plt.axis('off')
    
    work_dir = "/mnt/c/Users/User/Documents/agl;agmlaslgm/traffic_flows/"
    filename = work_dir + visualization_dir + "/network_visualization.png"
    print(filename)
    plt.savefig(filename)
    plt.close()

od_matrix = {
    'Res1': {
        'Downtown': 120,
    },
    'Res2': {
        'University': 30
    },
    'Res3': {
        'Downtown': 70,
    },
    'Downtown': {
        'Res1': 20
    }
}
compare_approaches(od_matrix, 'Downtown', 30)