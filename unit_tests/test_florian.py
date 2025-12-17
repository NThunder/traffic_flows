import unittest
from algos.florian import find_optimal_strategy, assign_demand, compute_sf, parse_gtfs
from algos.lateness_prob_florian import calculate_lateness_probability, find_optimal_strategy as lp_find_optimal_strategy, assign_demand as lp_assign_demand, compute_sf as lp_compute_sf
from algos.time_arrived_florian import find_optimal_strategy as ta_find_optimal_strategy, assign_demand as ta_assign_demand, compute_sf as ta_compute_sf
from utils import Link, Strategy, SFResult, Volumes
import tempfile
import os
import csv


class TestFlorianAlgorithms(unittest.TestCase):
    
    def setUp(self):
        # Создаем тестовые данные для всех алгоритмов
        self.test_links = [
            Link("A", "B", "1", 10, 15),
            Link("B", "C", "1", 15, 15),
            Link("A", "C", "2", 30, 30)
        ]
        
        self.test_stops = {"A", "B", "C"}
        self.od_matrix = {"A": {"C": 100}}
        self.destination = "C"
    
    def test_find_optimal_strategy(self):
        """Тест функции find_optimal_strategy из оригинального алгоритма Флориана"""
        result = find_optimal_strategy(self.test_links, self.test_stops, self.destination)
        
        # Проверяем, что результат является объектом класса Strategy
        self.assertIsInstance(result, Strategy)
        
        # Проверяем, что метки и частоты установлены
        self.assertIn(self.destination, result.labels)
        self.assertIn(self.destination, result.freqs)
        
        # Убедимся, что стоимость до цели равна 0
        self.assertEqual(result.labels[self.destination], 0.0)
    
    def test_assign_demand(self):
        """Тест функции assign_demand из оригинального алгоритма Флориана"""
        optimal_strategy = find_optimal_strategy(self.test_links, self.test_stops, self.destination)
        volumes = assign_demand(self.test_links, self.test_stops, optimal_strategy, self.od_matrix, self.destination)
        
        # Проверяем, что результат является объектом класса Volumes
        self.assertIsInstance(volumes, Volumes)
        
        # Проверяем, что объемы узлов содержат все остановки
        for stop in self.test_stops:
            self.assertIn(stop, volumes.nodes)
    
    def test_calculate_flow_volumes(self):
        """Тест функции calculate_flow_volumes через assign_demand"""
        optimal_strategy = find_optimal_strategy(self.test_links, self.test_stops, self.destination)
        volumes = assign_demand(self.test_links, self.test_stops, optimal_strategy, self.od_matrix, self.destination)
        
        # Проверяем, что суммарные объемы соответствуют ожиданиям
        total_volume = sum(abs(v) for v in volumes.nodes.values())
        # Объемы должны быть больше 0
        self.assertGreater(total_volume, 0)
    
    def test_compute_sf(self):
        """Тест полной функции compute_sf из оригинального алгоритма Флориана"""
        result = compute_sf(self.test_links, self.test_stops, self.destination, self.od_matrix)
        
        # Проверяем, что результат является объектом класса SFResult
        self.assertIsInstance(result, SFResult)
        
        # Проверяем, что стратегия и объемы существуют
        self.assertIsNotNone(result.strategy)
        self.assertIsNotNone(result.volumes)
    
    def test_calculate_lateness_probability(self):
        """Тест функции calculate_lateness_probability из алгоритма с вероятностью опоздания"""
        # Тест с нулевым стандартным отклонением
        prob1 = calculate_lateness_probability(10, 0, 15)
        self.assertEqual(prob1, 1.0)  # Уложились в дедлайн
        
        prob2 = calculate_lateness_probability(15, 0, 10)
        self.assertEqual(prob2, 0.0)  # Не уложились в дедлайн
        
        # Тест с положительным стандартным отклонением
        prob3 = calculate_lateness_probability(10, 2, 15)
        self.assertGreaterEqual(prob3, 0.0)
        self.assertLessEqual(prob3, 1.0)
    
    def test_lateness_prob_find_optimal_strategy(self):
        """Тест функции find_optimal_strategy из алгоритма с вероятностью опоздания"""
        result = lp_find_optimal_strategy(self.test_links, self.test_stops, self.destination, arrival_deadline=50)
        
        # Проверяем, что результат является объектом класса Strategy
        self.assertIsInstance(result, Strategy)
        
        # Проверяем, что вероятности находятся в диапазоне [0, 1]
        for stop, prob in result.labels.items():
            self.assertGreaterEqual(prob, 0.0)
            self.assertLessEqual(prob, 1.0)
    
    def test_lateness_prob_assign_demand(self):
        """Тест функции assign_demand из алгоритма с вероятностью опоздания"""
        optimal_strategy = lp_find_optimal_strategy(self.test_links, self.test_stops, self.destination, arrival_deadline=50)
        volumes = lp_assign_demand(self.test_links, self.test_stops, optimal_strategy, self.od_matrix, self.destination)
        
        # Проверяем, что результат является объектом класса Volumes
        self.assertIsInstance(volumes, Volumes)
        
        # Проверяем, что объемы узлов содержат все остановки
        for stop in self.test_stops:
            self.assertIn(stop, volumes.nodes)
    
    def test_lateness_prob_compute_sf(self):
        """Тест полной функции compute_sf из алгоритма с вероятностью опоздания"""
        result = lp_compute_sf(self.test_links, self.test_stops, self.destination, self.od_matrix, arrival_deadline=50)
        
        # Проверяем, что результат является объектом класса SFResult
        self.assertIsInstance(result, SFResult)
        
        # Проверяем, что стратегия и объемы существуют
        self.assertIsNotNone(result.strategy)
        self.assertIsNotNone(result.volumes)
    
    def test_time_arrived_find_optimal_strategy(self):
        """Тест функции find_optimal_strategy из алгоритма с временем прибытия"""
        result = ta_find_optimal_strategy(self.test_links, self.test_stops, self.destination, T=50)
        
        # Проверяем, что результат является объектом класса Strategy
        self.assertIsInstance(result, Strategy)
        
        # Проверяем, что mean_var содержит кортежи (mean, var)
        for stop, mv in result.labels.items():
            self.assertIsInstance(mv, tuple)
            self.assertEqual(len(mv), 2)
    
    def test_time_arrived_assign_demand(self):
        """Тест функции assign_demand из алгоритма с временем прибытия"""
        optimal_strategy = ta_find_optimal_strategy(self.test_links, self.test_stops, self.destination, T=50)
        volumes = ta_assign_demand(self.test_links, self.test_stops, optimal_strategy, self.od_matrix, self.destination)
        
        # Проверяем, что результат является объектом класса Volumes
        self.assertIsInstance(volumes, Volumes)
        
        # Проверяем, что объемы узлов содержат все остановки
        for stop in self.test_stops:
            self.assertIn(stop, volumes.nodes)
    
    def test_time_arrived_compute_sf(self):
        """Тест полной функции compute_sf из алгоритма с временем прибытия"""
        result = ta_compute_sf(self.test_links, self.test_stops, self.destination, self.od_matrix, T=50)
        
        # Проверяем, что результат является объектом класса SFResult
        self.assertIsInstance(result, SFResult)
        
        # Проверяем, что стратегия и объемы существуют
        self.assertIsNotNone(result.strategy)
        self.assertIsNotNone(result.volumes)
    
    def test_parse_gtfs_with_sample_data(self):
        """Тест функции parse_gtfs с использованием sample_data"""
        # Создаем временный каталог с GTFS данными
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем файлы в соответствии с sample_data
            stops_path = os.path.join(temp_dir, 'stops.txt')
            with open(stops_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['stop_id', 'stop_name', 'lat', 'lon'])
                writer.writerow(['A', 'Stop A', '55.7558', '37.6176'])
                writer.writerow(['B', 'Stop B', '55.7483', '37.6155'])
                writer.writerow(['C', 'Stop C', '55.7597', '37.6154'])
            
            routes_path = os.path.join(temp_dir, 'routes.txt')
            with open(routes_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['route_id', 'route_name', 'route_type'])
                writer.writerow(['1', 'Route 1', '3'])
                writer.writerow(['2', 'Route 2', '3'])
            
            trips_path = os.path.join(temp_dir, 'trips.txt')
            with open(trips_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['trip_id', 'route_id', 'service_id'])
                writer.writerow(['1_1', '1', 'weekday'])
                writer.writerow(['1_2', '1', 'weekday'])
                writer.writerow(['2_1', '2', 'weekday'])
            
            stop_times_path = os.path.join(temp_dir, 'stop_times.txt')
            with open(stop_times_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence'])
                writer.writerow(['1_1', '08:00:00', '08:00:00', 'A', '0'])
                writer.writerow(['1_1', '08:10:00', '08:10:00', 'B', '1'])
                writer.writerow(['1_1', '08:25:00', '08:25:00', 'C', '2'])
                writer.writerow(['1_2', '08:30:00', '08:30:00', 'A', '0'])
                writer.writerow(['1_2', '08:40:00', '08:40:00', 'B', '1'])
                writer.writerow(['1_2', '08:55:00', '08:55:00', 'C', '2'])
                writer.writerow(['2_1', '08:05:00', '08:05:00', 'B', '0'])
                writer.writerow(['2_1', '08:20:00', '08:20:00', 'C', '1'])
            
            calendar_path = os.path.join(temp_dir, 'calendar.txt')
            with open(calendar_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['service_id', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'start_date', 'end_date'])
                writer.writerow(['weekday', '1', '1', '1', '1', '1', '0', '0', '20250101', '20251231'])
            
            # Тестируем парсинг
            all_links, all_stops = parse_gtfs(temp_dir, limit=100)
            
            # Проверяем, что данные были загружены
            self.assertGreater(len(all_links), 0)
            self.assertGreater(len(all_stops), 0)
            
            # Проверяем, что все остановки из данных присутствуют
            expected_stops = {'A', 'B', 'C'}
            self.assertTrue(expected_stops.issubset(all_stops))


if __name__ == '__main__':
    unittest.main()