import math
import unittest
from algos.florian import find_optimal_strategy, assign_demand, compute_sf, compute_sf_improved
from utils import Link, Strategy, SFResult, Volumes

class Test_Florian_NetThreeStopsThreeLinks(unittest.TestCase):
    def setUp(self):
        self.links = [
            Link("A", "B", "1", 10, 15),
            Link("B", "C", "1", 15, 15),
            Link("A", "C", "2", 30, 30)
        ]
        
        self.stops = {"A", "B", "C"}
        self.od_matrix = {"A": {"C": 100}}
        self.destination = "C"

    def check_frequencies_in_node(self, node, links_from_node: list[Link], strategy: Strategy):
        sum_freq = 0.0
        for link in links_from_node:
            freq = 1.0 / link.headway
            sum_freq += freq

        self.assertAlmostEqual(strategy.freqs[node], sum_freq, places=5)
    
    def test_find_optimal_strategy(self):
        result = find_optimal_strategy(self.links, self.stops, self.destination)
        
        node_to_links : dict[str, list[Link]] = {}
        for node in self.stops:
            for link in self.links:
                if node not in node_to_links:
                    node_to_links[node] = []

                if link.from_node == node:
                    node_to_links[node].append(link)

        for node in self.stops:
            self.check_frequencies_in_node(node, node_to_links[node], result)
    
    def test_sorted_optimal_strategy(self):
        optimal_strategy = find_optimal_strategy(self.links, self.stops, self.destination)
        assign_demand(self.links, self.stops, optimal_strategy, self.od_matrix, self.destination)

        prev_val = math.inf
        for a in optimal_strategy.a_set:
            cur_val = optimal_strategy.labels[a.to_node] + a.travel_cost
            self.assertGreater(prev_val, cur_val)
            prev_val = cur_val

    def test_assign_demand(self):
        optimal_strategy = find_optimal_strategy(self.links, self.stops, self.destination)
        volumes = assign_demand(self.links, self.stops, optimal_strategy, self.od_matrix, self.destination)
        
        self.assertAlmostEqual(volumes.nodes[self.destination], 100.0, places=5)
    

class Test_Florian_NetThreeStopsTwoLinks(unittest.TestCase):
    def setUp(self):
        # A -> B -> C
        self.links = [
            Link(from_node="A", to_node="B", route_id="1", travel_cost=10, headway=15),
            Link(from_node="B", to_node="C", route_id="1", travel_cost=15, headway=15)
        ]
        
        self.stops = {"A", "B", "C"}
        self.od_matrix = {"A": {"C": 10}}
        self.destination = "C"

    def test_florian_algorithm_logic(self):
        strategy = find_optimal_strategy(self.links, self.stops, self.destination)
        volumes = assign_demand(self.links, self.stops, strategy, self.od_matrix, self.destination)
        
        self.assertAlmostEqual(volumes.nodes["A"], 10.0, places=5)
        self.assertAlmostEqual(volumes.nodes["B"], 10.0, places=5)
        self.assertAlmostEqual(volumes.nodes["C"], 10.0, places=5)
        
        self.assertAlmostEqual(volumes.links["A"]["B"], 10.0, places=5)
        self.assertAlmostEqual(volumes.links["B"]["C"], 10.0, places=5)
    
class Test_Florian_NetFourStopsFourLinks(unittest.TestCase): # тестим обьемы
    def setUp(self):
        # A -> B -> C и A -> D -> C
        self.links = [
            Link("A", "B", "1", 10, 10),  # A-B-C
            Link("B", "C", "1", 15, 10),
            Link("A", "D", "2", 12, 20),  # A-D-C (дешевле но с меньшей частотой)
            Link("D", "C", "2", 13, 20)
        ]
        
        self.stops = {"A", "B", "C", "D"}
        self.od_matrix = {"A": {"C": 100}}
        self.destination = "C"
        
    def test_volumes(self):
        strategy = find_optimal_strategy(self.links, self.stops, self.destination)
        volumes = assign_demand(self.links, self.stops, strategy, self.od_matrix, self.destination)
        
        self.assertAlmostEqual(volumes.nodes["A"],       100, places=1)
        self.assertAlmostEqual(volumes.nodes["B"], 2/3 * 100, places=1)
        self.assertAlmostEqual(volumes.nodes["C"],       100, places=1)
        self.assertAlmostEqual(volumes.nodes["D"], 1/3 * 100, places=1)
        
        # сумма объемов в промежуточных узлах близка к 100
        intermediate_sum = sum(volumes.nodes[stop] for stop in self.stops if stop not in ["A", "C"])
        self.assertAlmostEqual(intermediate_sum, 100, 5)
        
        # dumb check
        for from_node in volumes.links:
            for to_node in volumes.links[from_node]:
                self.assertGreaterEqual(volumes.links[from_node][to_node], 0)
    
    def test_output_labels(self):
        result = find_optimal_strategy(self.links, self.stops, self.destination)
        
        self.assertIsInstance(result, Strategy)
        for stop, time in result.labels.items():
            self.assertGreaterEqual(time, 0.0)


class Test_Florian_NetThreeStopsThreeLinks2(unittest.TestCase):
    def setUp(self):
        self.links = [
            Link("A", "B", "route1", 5, 15),  # 10 минут в пути, интервал 15 мин
            Link("B", "C", "route1", 5, 15),  # 15 минут в пути, интервал 15 мин
            Link("A", "C", "route2", 30, 5),   # 30 минут в пути, интервал 5 мин
        ]
        
        self.stops = {"A", "B", "C"}
        self.od_matrix = {"A": {"C": 100}}
        self.destination = "C"

    def test_same_route_improvement(self):
        result = compute_sf_improved(self.links, self.stops, self.destination, self.od_matrix)
    
        print(f"Обобщенные затраты из A в C: {result.strategy.labels['A']}")
        print(f"Обобщенные затраты в C (должны быть 0): {result.strategy.labels['C']}")
        
        # Время по маршруту A -> B -> C составляет 10 + 15 = 25 минут
        # При правильной реализации это должно быть близко к оптимальному времени
        # без лишнего ожидания на остановке B
        
        print(f"Оптимальные связи (a_set): {len(result.strategy.a_set)}")
        for link in result.strategy.a_set:
            print(f"  {link.from_node} -> {link.to_node} по маршруту {link.route_id}")


if __name__ == '__main__':
    unittest.main()