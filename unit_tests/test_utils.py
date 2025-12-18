import unittest
from algos.florian import parse_gtfs
import tempfile
import os
import csv

class TestUtils(unittest.TestCase):
    def test_parse_gtfs_with_sample_data(self):
        # Создаем временный каталог с GTFS данными
        with tempfile.TemporaryDirectory() as temp_dir:
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
            
            all_links, all_stops = parse_gtfs(temp_dir, limit=100)
            
            self.assertGreater(len(all_links), 0)
            self.assertGreater(len(all_stops), 0)
            
            expected_stops = {'A', 'B', 'C'} # все остановки из данных присутствуют
            self.assertTrue(expected_stops.issubset(all_stops))
