import unittest
import matplotlib.pyplot as plt
import networkx as nx
import tempfile
import os
import csv
from algos.florian import compute_sf as florian_compute_sf, parse_gtfs as florian_parse_gtfs
from algos.time_arrived_florian import compute_sf as ta_compute_sf, parse_gtfs as ta_parse_gtfs
from utils import Link


class TestVisualization(unittest.TestCase):
    def setUp(self):
        self.links = [
            Link("A", "B", "1", 10, 15, 10),
            Link("B", "C", "1", 15, 15, 15),
            Link("A", "C", "2", 30, 5),
            Link("B", "D", "3", 20, 20),
            Link("C", "D", "4", 10, 10)
        ]
        
        self.stops = {"A", "B", "C", "D"}
        self.od_matrix = {"A": {"D": 100}, "B": {"D": 50}}
        self.destination = "D"
        
        self.visualization_dir = "unit_tests/visualizations"
        os.makedirs(self.visualization_dir, exist_ok=True)
    
    def create_simple_gtfs_data(self, temp_dir):
        """Создает простые GTFS данные для тестирования"""
        stops_path = os.path.join(temp_dir, 'stops.txt')
        with open(stops_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['stop_id', 'stop_name', 'lat', 'lon'])
            writer.writerow(['A', 'Stop A', '55.7558', '37.6176'])
            writer.writerow(['B', 'Stop B', '55.7483', '37.6155'])
            writer.writerow(['C', 'Stop C', '55.7597', '37.6154'])
            writer.writerow(['D', 'Stop D', '55.7402', '37.6150'])
        
        routes_path = os.path.join(temp_dir, 'routes.txt')
        with open(routes_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['route_id', 'route_name', 'route_type'])
            writer.writerow(['1', 'Route 1', '3'])
            writer.writerow(['2', 'Route 2', '3'])
            writer.writerow(['3', 'Route 3', '3'])
            writer.writerow(['4', 'Route 4', '3'])
        
        trips_path = os.path.join(temp_dir, 'trips.txt')
        with open(trips_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['trip_id', 'route_id', 'service_id'])
            writer.writerow(['1_1', '1', 'weekday'])
            writer.writerow(['2_1', '2', 'weekday'])
            writer.writerow(['3_1', '3', 'weekday'])
            writer.writerow(['4_1', '4', 'weekday'])
        
        stop_times_path = os.path.join(temp_dir, 'stop_times.txt')
        with open(stop_times_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence'])
            writer.writerow(['1_1', '08:00:00', '08:00:00', 'A', '0'])
            writer.writerow(['1_1', '08:10:00', '08:10:00', 'B', '1'])
            writer.writerow(['1_1', '08:25:00', '08:25:00', 'C', '2'])
            writer.writerow(['2_1', '08:05:00', '08:05:00', 'A', '0'])
            writer.writerow(['2_1', '08:35:00', '08:35:00', 'C', '1'])
            writer.writerow(['3_1', '08:15:00', '08:15:00', 'B', '0'])
            writer.writerow(['3_1', '08:35:00', '08:35:00', 'D', '1'])
            writer.writerow(['4_1', '08:25:00', '08:25:00', 'C', '0'])
            writer.writerow(['4_1', '08:35:00', '08:35:00', 'D', '1'])
        
        calendar_path = os.path.join(temp_dir, 'calendar.txt')
        with open(calendar_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['service_id', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'start_date', 'end_date'])
            writer.writerow(['weekday', '1', '1', '1', '1', '1', '0', '0', '20250101', '20251231'])
    
    def test_network_visualization(self):
        """Тест визуализации простой транспортной сети"""
        G = nx.DiGraph()
        
        for stop in self.stops:
            G.add_node(stop)
        
        for link in self.links:
            G.add_edge(link.from_node, link.to_node, weight=link.travel_cost, route=link.route_id)
        
        plt.figure(figsize=(10, 8))
        pos = nx.spring_layout(G)
        
        nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=1500)
        
        nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20)
        
        nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
        
        edge_labels = {(link.from_node, link.to_node): f"{link.travel_cost}min\n({link.route_id})"
                      for link in self.links}
        nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8)
        
        plt.title("Простая транспортная сеть для тестирования алгоритмов")
        plt.axis('off')
        
        filename = os.path.join(self.visualization_dir, "network_visualization.png")
        plt.savefig(filename)
        plt.close()
        
        self.assertTrue(os.path.exists(filename))
    
    def test_florian_algorithm_with_visualization(self):
        """Тест алгоритма Флориана с визуализацией результатов"""
        G = nx.DiGraph()
        
        for stop in self.stops:
            G.add_node(stop)
        
        for link in self.links:
            G.add_edge(link.from_node, link.to_node, weight=link.travel_cost, route=link.route_id)
        
        result = florian_compute_sf(self.links, self.stops, self.destination, self.od_matrix)
        
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G, seed=42)
        
        nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=1500)
        
        nx.draw_networkx_nodes(G, pos, nodelist=[self.destination], node_color='red', node_size=1500)
        
        nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20)
        
        strategy_edges = [(link.from_node, link.to_node) for link in result.strategy.a_set]
        nx.draw_networkx_edges(G, pos, edgelist=strategy_edges, edge_color='green',
                              arrows=True, arrowsize=20, width=2)
        
        nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
        
        edge_labels = {}
        for link in self.links:
            volume = result.volumes.links.get(link.from_node, {}).get(link.to_node, 0)
            edge_labels[(link.from_node, link.to_node)] = f"{link.travel_cost}min\n({volume:.1f})"
        
        nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8)
        
        plt.title("Алгоритм Флориана - Оптимальная стратегия (зеленые ребра)")
        plt.axis('off')
        
        filename = os.path.join(self.visualization_dir, "florian_algorithm_visualization.png")
        plt.savefig(filename)
        plt.close()
        
        self.assertTrue(os.path.exists(filename))
    
    def test_time_arrived_algorithm_with_visualization(self):
        """Тест алгоритма с временем прибытия с визуализацией результатов"""
        G = nx.DiGraph()
        
        for stop in self.stops:
            G.add_node(stop)
        
        for link in self.links:
            G.add_edge(link.from_node, link.to_node, weight=link.travel_cost, route=link.route_id)
        
        result = ta_compute_sf(self.links, self.stops, self.destination,
                              self.od_matrix, T=60)
        
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G, seed=42)
        
        nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=1500)
        
        nx.draw_networkx_nodes(G, pos, nodelist=[self.destination], node_color='red', node_size=1500)
        
        nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20)
        
        strategy_edges = [(link.from_node, link.to_node) for link in result.strategy.a_set]
        nx.draw_networkx_edges(G, pos, edgelist=strategy_edges, edge_color='purple',
                              arrows=True, arrowsize=20, width=2)
        
        nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
        
        edge_labels = {}
        for link in self.links:
            volume = result.volumes.links.get(link.from_node, {}).get(link.to_node, 0)
            edge_labels[(link.from_node, link.to_node)] = f"{link.travel_cost}min\n({volume:.1f})"
        
        nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8)
        
        plt.title("Алгоритм с временем прибытия - Оптимальная стратегия (фиолетовые ребра)")
        plt.axis('off')
        
        filename = os.path.join(self.visualization_dir, "time_arrived_algorithm_visualization.png")
        plt.savefig(filename)
        plt.close()
        
        self.assertTrue(os.path.exists(filename))
    
    def test_gtfs_based_visualization(self):
        """Тест визуализации на основе GTFS данных"""
        with tempfile.TemporaryDirectory() as temp_dir:
            self.create_simple_gtfs_data(temp_dir)
            
            all_links, all_stops = florian_parse_gtfs(temp_dir, limit=100)
            
            G = nx.DiGraph()
            
            for stop in all_stops:
                G.add_node(stop)
            
            for link in all_links:
                G.add_edge(link.from_node, link.to_node, weight=link.travel_cost, route=link.route_id)
            
            od_matrix = {"A": {"D": 100}}
            destination = "D"
            
            result = florian_compute_sf(all_links, all_stops, destination, od_matrix)
            
            plt.figure(figsize=(12, 8))
            pos = nx.spring_layout(G, seed=42)
            
            nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=1500)
            
            nx.draw_networkx_nodes(G, pos, nodelist=[destination], node_color='red', node_size=1500)
            
            nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20)
            
            strategy_edges = [(link.from_node, link.to_node) for link in result.strategy.a_set]
            nx.draw_networkx_edges(G, pos, edgelist=strategy_edges, edge_color='green',
                                  arrows=True, arrowsize=20, width=2)
            
            nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
            
            edge_labels = {}
            for link in all_links:
                volume = result.volumes.links.get(link.from_node, {}).get(link.to_node, 0)
                edge_labels[(link.from_node, link.to_node)] = f"{link.travel_cost}min\n({volume:.1f})"
            
            nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8)
            
            plt.title("Алгоритм Флориана на основе GTFS - Оптимальная стратегия")
            plt.axis('off')
            
            filename = os.path.join(self.visualization_dir, "gtfs_based_visualization.png")
            plt.savefig(filename)
            plt.close()
            
            self.assertTrue(os.path.exists(filename))


if __name__ == '__main__':
    unittest.main()