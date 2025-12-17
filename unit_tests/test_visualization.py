import unittest
import matplotlib.pyplot as plt
import networkx as nx
import tempfile
import os
import csv
from algos.florian import compute_sf as florian_compute_sf, parse_gtfs as florian_parse_gtfs
from algos.lateness_prob_florian import compute_sf as lp_compute_sf, parse_gtfs as lp_parse_gtfs
from algos.time_arrived_florian import compute_sf as ta_compute_sf, parse_gtfs as ta_parse_gtfs
from utils import Link


class TestVisualization(unittest.TestCase):
    
    def setUp(self):
        # Создаем простую тестовую сеть для визуализации
        self.test_links = [
            Link("A", "B", "1", 10, 15, 10, 2),
            Link("B", "C", "1", 15, 15, 15, 3),
            Link("A", "C", "2", 30, 5),
            Link("B", "D", "3", 20, 20, 2),
            Link("C", "D", "4", 10, 10, 1)
        ]
        
        self.test_stops = {"A", "B", "C", "D"}
        self.od_matrix = {"A": {"D": 100}, "B": {"D": 50}}
        self.destination = "D"
        
        # Создаем директорию для визуализаций, если она не существует
        self.visualization_dir = "unit_tests/visualizations"
        os.makedirs(self.visualization_dir, exist_ok=True)
    
    def create_simple_gtfs_data(self, temp_dir):
        """Создает простые GTFS данные для тестирования"""
        # Создаем файлы в соответствии с sample_data
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
        # Создаем граф
        G = nx.DiGraph()
        
        # Добавляем узлы
        for stop in self.test_stops:
            G.add_node(stop)
        
        # Добавляем ребра
        for link in self.test_links:
            G.add_edge(link.from_node, link.to_node, weight=link.travel_cost, route=link.route_id)
        
        # Создаем визуализацию
        plt.figure(figsize=(10, 8))
        pos = nx.spring_layout(G)
        
        # Рисуем узлы
        nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=1500)
        
        # Рисуем ребра
        nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20)
        
        # Добавляем метки узлов
        nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
        
        # Добавляем метки ребер
        edge_labels = {(link.from_node, link.to_node): f"{link.travel_cost}min\n({link.route_id})" 
                      for link in self.test_links}
        nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8)
        
        plt.title("Простая транспортная сеть для тестирования алгоритмов")
        plt.axis('off')
        
        # Сохраняем изображение в папку визуализаций
        filename = os.path.join(self.visualization_dir, "network_visualization.png")
        plt.savefig(filename)
        plt.close()
        
        # Проверяем, что файл был создан
        self.assertTrue(os.path.exists(filename))
    
    def test_florian_algorithm_with_visualization(self):
        """Тест алгоритма Флориана с визуализацией результатов"""
        # Создаем граф для визуализации
        G = nx.DiGraph()
        
        # Добавляем узлы
        for stop in self.test_stops:
            G.add_node(stop)
        
        # Добавляем ребра
        for link in self.test_links:
            G.add_edge(link.from_node, link.to_node, weight=link.travel_cost, route=link.route_id)
        
        # Вычисляем результаты алгоритма
        result = florian_compute_sf(self.test_links, self.test_stops, self.destination, self.od_matrix)
        
        # Создаем визуализацию
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G, seed=42)  # Для воспроизводимости
        
        # Рисуем узлы
        nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=1500)
        
        # Выделяем целевой узел
        nx.draw_networkx_nodes(G, pos, nodelist=[self.destination], node_color='red', node_size=1500)
        
        # Рисуем ребра
        nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20)
        
        # Выделяем ребра, входящие в оптимальную стратегию
        strategy_edges = [(link.from_node, link.to_node) for link in result.strategy.a_set]
        nx.draw_networkx_edges(G, pos, edgelist=strategy_edges, edge_color='green', 
                              arrows=True, arrowsize=20, width=2)
        
        # Добавляем метки узлов
        nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
        
        # Добавляем метки ребер с объемами
        edge_labels = {}
        for link in self.test_links:
            volume = result.volumes.links.get(link.from_node, {}).get(link.to_node, 0)
            edge_labels[(link.from_node, link.to_node)] = f"{link.travel_cost}min\n({volume:.1f})"
        
        nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8)
        
        plt.title("Алгоритм Флориана - Оптимальная стратегия (зеленые ребра)")
        plt.axis('off')
        
        # Сохраняем изображение в папку визуализаций
        filename = os.path.join(self.visualization_dir, "florian_algorithm_visualization.png")
        plt.savefig(filename)
        plt.close()
        
        # Проверяем, что файл был создан
        self.assertTrue(os.path.exists(filename))
    
    def test_lateness_prob_algorithm_with_visualization(self):
        """Тест алгоритма с вероятностью опоздания с визуализацией результатов"""
        # Создаем граф для визуализации
        G = nx.DiGraph()
        
        # Добавляем узлы
        for stop in self.test_stops:
            G.add_node(stop)
        
        # Добавляем ребра
        for link in self.test_links:
            G.add_edge(link.from_node, link.to_node, weight=link.travel_cost, route=link.route_id)
        
        # Вычисляем результаты алгоритма
        result = lp_compute_sf(self.test_links, self.test_stops, self.destination, 
                              self.od_matrix, arrival_deadline=50)
        
        # Создаем визуализацию
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G, seed=42)  # Для воспроизводимости
        
        # Рисуем узлы
        nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=1500)
        
        # Выделяем целевой узел
        nx.draw_networkx_nodes(G, pos, nodelist=[self.destination], node_color='red', node_size=1500)
        
        # Рисуем ребра
        nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20)
        
        # Выделяем ребра, входящие в оптимальную стратегию
        strategy_edges = [(link.from_node, link.to_node) for link in result.strategy.a_set]
        nx.draw_networkx_edges(G, pos, edgelist=strategy_edges, edge_color='orange', 
                              arrows=True, arrowsize=20, width=2)
        
        # Добавляем метки узлов
        nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
        
        # Добавляем метки ребер с объемами
        edge_labels = {}
        for link in self.test_links:
            volume = result.volumes.links.get(link.from_node, {}).get(link.to_node, 0)
            edge_labels[(link.from_node, link.to_node)] = f"{link.travel_cost}min\n({volume:.1f})"
        
        nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8)
        
        plt.title("Алгоритм с вероятностью опоздания - Оптимальная стратегия (оранжевые ребра)")
        plt.axis('off')
        
        # Сохраняем изображение в папку визуализаций
        filename = os.path.join(self.visualization_dir, "lateness_prob_algorithm_visualization.png")
        plt.savefig(filename)
        plt.close()
        
        # Проверяем, что файл был создан
        self.assertTrue(os.path.exists(filename))
    
    def test_time_arrived_algorithm_with_visualization(self):
        """Тест алгоритма с временем прибытия с визуализацией результатов"""
        # Создаем граф для визуализации
        G = nx.DiGraph()
        
        # Добавляем узлы
        for stop in self.test_stops:
            G.add_node(stop)
        
        # Добавляем ребра
        for link in self.test_links:
            G.add_edge(link.from_node, link.to_node, weight=link.travel_cost, route=link.route_id)
        
        # Вычисляем результаты алгоритма
        result = ta_compute_sf(self.test_links, self.test_stops, self.destination, 
                              self.od_matrix, T=60)
        
        # Создаем визуализацию
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G, seed=42)  # Для воспроизводимости
        
        # Рисуем узлы
        nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=1500)
        
        # Выделяем целевой узел
        nx.draw_networkx_nodes(G, pos, nodelist=[self.destination], node_color='red', node_size=1500)
        
        # Рисуем ребра
        nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20)
        
        # Выделяем ребра, входящие в оптимальную стратегию
        strategy_edges = [(link.from_node, link.to_node) for link in result.strategy.a_set]
        nx.draw_networkx_edges(G, pos, edgelist=strategy_edges, edge_color='purple', 
                              arrows=True, arrowsize=20, width=2)
        
        # Добавляем метки узлов
        nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
        
        # Добавляем метки ребер с объемами
        edge_labels = {}
        for link in self.test_links:
            volume = result.volumes.links.get(link.from_node, {}).get(link.to_node, 0)
            edge_labels[(link.from_node, link.to_node)] = f"{link.travel_cost}min\n({volume:.1f})"
        
        nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8)
        
        plt.title("Алгоритм с временем прибытия - Оптимальная стратегия (фиолетовые ребра)")
        plt.axis('off')
        
        # Сохраняем изображение в папку визуализаций
        filename = os.path.join(self.visualization_dir, "time_arrived_algorithm_visualization.png")
        plt.savefig(filename)
        plt.close()
        
        # Проверяем, что файл был создан
        self.assertTrue(os.path.exists(filename))
    
    def test_gtfs_based_visualization(self):
        """Тест визуализации на основе GTFS данных"""
        # Создаем временный каталог с GTFS данными
        with tempfile.TemporaryDirectory() as temp_dir:
            self.create_simple_gtfs_data(temp_dir)
            
            # Загружаем данные
            all_links, all_stops = florian_parse_gtfs(temp_dir, limit=100)
            
            # Создаем граф для визуализации
            G = nx.DiGraph()
            
            # Добавляем узлы
            for stop in all_stops:
                G.add_node(stop)
            
            # Добавляем ребра
            for link in all_links:
                G.add_edge(link.from_node, link.to_node, weight=link.travel_cost, route=link.route_id)
            
            # Определяем OD-матрицу и цель
            od_matrix = {"A": {"D": 100}}
            destination = "D"
            
            # Вычисляем результаты алгоритма
            result = florian_compute_sf(all_links, all_stops, destination, od_matrix)
            
            # Создаем визуализацию
            plt.figure(figsize=(12, 8))
            pos = nx.spring_layout(G, seed=42)  # Для воспроизводимости
            
            # Рисуем узлы
            nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=1500)
            
            # Выделяем целевой узел
            nx.draw_networkx_nodes(G, pos, nodelist=[destination], node_color='red', node_size=1500)
            
            # Рисуем ребра
            nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20)
            
            # Выделяем ребра, входящие в оптимальную стратегию
            strategy_edges = [(link.from_node, link.to_node) for link in result.strategy.a_set]
            nx.draw_networkx_edges(G, pos, edgelist=strategy_edges, edge_color='green', 
                                  arrows=True, arrowsize=20, width=2)
            
            # Добавляем метки узлов
            nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
            
            # Добавляем метки ребер с объемами
            edge_labels = {}
            for link in all_links:
                volume = result.volumes.links.get(link.from_node, {}).get(link.to_node, 0)
                edge_labels[(link.from_node, link.to_node)] = f"{link.travel_cost}min\n({volume:.1f})"
            
            nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8)
            
            plt.title("Алгоритм Флориана на основе GTFS - Оптимальная стратегия")
            plt.axis('off')
            
            # Сохраняем изображение в папку визуализаций
            filename = os.path.join(self.visualization_dir, "gtfs_based_visualization.png")
            plt.savefig(filename)
            plt.close()
            
            # Проверяем, что файл был создан
            self.assertTrue(os.path.exists(filename))


if __name__ == '__main__':
    unittest.main()