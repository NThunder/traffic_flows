import math
import unittest
from algos.time_arrived_florian import find_optimal_strategy, assign_demand
from utils import Link, Strategy, SFResult, Volumes


class Test_TimeArrivedFlorian_NetThreeStopsTwoLinks(unittest.TestCase):
    def setUp(self):
        # A -> B -> C
        self.links = [ # travel_cost here is optional
            Link("A", "B", "1", travel_cost=10, headway=15, mean_travel_time=10),
            Link("B", "C", "1", travel_cost=15, headway= 3, mean_travel_time=15)
        ]
        
        self.stops = {"A", "B", "C"}
        self.od_matrix = {"A": {"C": 100}}
        self.destination = "C"
        self.arrival_deadline = 60

    def test_algorithm_logic(self):
        strategy = find_optimal_strategy(self.links, self.stops, destination=self.destination, T=self.arrival_deadline)
        volumes = assign_demand(self.links, self.stops, strategy, self.od_matrix, self.destination)
        
        self.assertAlmostEqual(volumes.nodes["A"], 100.0, places=5)
        self.assertAlmostEqual(volumes.nodes["B"], 100.0, places=5)
        self.assertAlmostEqual(volumes.nodes["C"], 100.0, places=5)
        
        self.assertAlmostEqual(volumes.links["A"]["B"], 100.0, places=5)
        self.assertAlmostEqual(volumes.links["B"]["C"], 100.0, places=5)

    def test_output_labels(self):
        result = find_optimal_strategy(self.links, self.stops, destination=self.destination, T=50)
        
        self.assertIsInstance(result, Strategy)
        for stop, mv in result.labels.items():
            self.assertIsInstance(mv, tuple)
            self.assertEqual(len(mv), 2)

            mean, var = mv

            self.assertGreaterEqual(var, 0.0)

            self.assertFalse(math.isnan(mean))
            self.assertFalse(math.isnan(var))

            self.assertFalse(math.isinf(mean))
            self.assertFalse(math.isinf(var))

class Test_TimeArrivedFlorian_NetFourStopsFourLinks(unittest.TestCase): 
    def setUp(self):
        # A -> B -> C и A -> D -> C
        self.links = [
            Link("A", "B", "1", travel_cost=10, headway=10, mean_travel_time=10),
            Link("B", "C", "1", travel_cost=15, headway=10, mean_travel_time=15),
            Link("A", "D", "2", travel_cost=12, headway=20, mean_travel_time=12),
            Link("D", "C", "2", travel_cost=13, headway=20, mean_travel_time=13)
        ]
        
        self.stops = {"A", "B", "C", "D"}
        self.od_matrix = {"A": {"C": 100}}
        self.destination = "C"
        self.arrival_deadline = 40

    def test_volumes(self):
        strategy = find_optimal_strategy(self.links, self.stops, self.destination, self.arrival_deadline)
        volumes = assign_demand(self.links, self.stops, strategy, self.od_matrix, self.destination)
        
        self.assertAlmostEqual(volumes.nodes["A"], 100, places=5)
        self.assertAlmostEqual(volumes.nodes["B"], 100, places=5)
        self.assertAlmostEqual(volumes.nodes["C"], 100, places=5)
        self.assertAlmostEqual(volumes.nodes["D"], 0, places=5)

        # all people go this way
        self.assertAlmostEqual(volumes.links["A"]["B"], 100, places=5)
        self.assertAlmostEqual(volumes.links["B"]["C"], 100, places=5)

        # no people go this way
        self.assertAlmostEqual(volumes.links["A"]["D"], 0, places=5)
        self.assertAlmostEqual(volumes.links["D"]["C"], 0, places=5)
        
        intermediate_sum = sum(volumes.nodes[stop] for stop in self.stops if stop not in ["A", "C"])
        self.assertAlmostEqual(intermediate_sum, 100, places=5)