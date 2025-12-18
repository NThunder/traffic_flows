import unittest
from algos.lateness_prob_florian import calculate_lateness_probability, find_optimal_strategy, assign_demand
from utils import Link, Strategy, SFResult, Volumes


class Test_LatenessProbabilityFlorian_NetThreeStopsTwoLinks(unittest.TestCase):
    def setUp(self):
        # A -> B -> C
        self.links = [
            Link("A", "B", "1", travel_cost=10, headway=15, mean_travel_time=10, std_travel_time=2),
            Link("B", "C", "1", travel_cost=15, headway=15, mean_travel_time=3)
        ]
        
        self.stops = {"A", "B", "C"}
        self.od_matrix = {"A": {"C": 100}}
        self.destination = "C"
        self.arrival_deadline = 50

    def test_algorithm_logic(self):
        strategy = find_optimal_strategy(self.links, self.stops, self.destination, self.arrival_deadline)
        volumes = assign_demand(self.links, self.stops, strategy, self.od_matrix, self.destination)
        
        self.assertGreaterEqual(volumes.nodes["A"], 0)
        self.assertLessEqual(volumes.nodes["C"], 0)

        self.assertLessEqual(volumes.nodes["B"], 100.1)
        self.assertGreaterEqual(volumes.nodes["B"], -0.1)

    def test_output_labels(self):
        result = find_optimal_strategy(self.links, self.stops, self.destination, arrival_deadline=50)
        
        self.assertIsInstance(result, Strategy)
        for stop, prob in result.labels.items():
            self.assertGreaterEqual(prob, 0.0)
            self.assertLessEqual(prob, 1.0)


class Test_LatenessProbabilityFlorian_Unit(unittest.TestCase):
    def test_calculate_lateness_probability(self):
        prob1 = calculate_lateness_probability(mean_time=10, std_time=0, arrival_deadline=15)
        self.assertEqual(prob1, 1.0)  # Уложились в дедлайн
        
        prob2 = calculate_lateness_probability(mean_time=15, std_time=0, arrival_deadline=10)
        self.assertEqual(prob2, 0.0)  # Не уложились в дедлайн
        
        prob3 = calculate_lateness_probability(mean_time=10, std_time=2, arrival_deadline=15)
        self.assertGreaterEqual(prob3, 0.0)
        self.assertLessEqual(prob3, 1.0)


class Test_LatenessProbabilityFlorian_NetFourStopsFourLinks(unittest.TestCase):
    def setUp(self):
        # A -> B -> C и A -> D -> C
        self.links = [
            Link("A", "B", "1", travel_cost=10, headway=10, mean_travel_time=10, std_travel_time=1),
            Link("B", "C", "1", travel_cost=15, headway=10, mean_travel_time=15, std_travel_time=1),
            Link("A", "D", "2", travel_cost=12, headway=20, mean_travel_time=12, std_travel_time=5),
            Link("D", "C", "2", travel_cost=13, headway=20, mean_travel_time=13, std_travel_time=5)
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
        self.assertAlmostEqual(volumes.nodes["C"], 0, places=5)
        self.assertAlmostEqual(volumes.nodes["D"], 0, places=5)

        # all people go this way
        self.assertAlmostEqual(volumes.links["A"]["B"], 100, places=5)
        self.assertAlmostEqual(volumes.links["B"]["C"], 100, places=5)

        # no people go this way
        self.assertAlmostEqual(volumes.links["A"]["D"], 0, places=5)
        self.assertAlmostEqual(volumes.links["D"]["C"], 0, places=5)
        
        intermediate_sum = sum(volumes.nodes[stop] for stop in self.stops if stop not in ["A", "C"])
        self.assertLessEqual(abs(intermediate_sum), 100.1)
    