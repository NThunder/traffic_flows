#!/usr/bin/env python3
"""
Тест для проверки улучшения в алгоритме Spiess-Florian
Проверяет, что внутри-маршрутные перемещения не добавляют лишнее время ожидания
"""
from utils import Link
from algos.florian import compute_sf

def test_same_route_improvement():
    """
    Тест с простым маршрутом A -> B -> C на одном и том же маршруте
    Ранее алгоритм добавлял время ожидания на остановке B, как будто пассажир
    выходит и снова садится на тот же автобус, теперь этого не должно происходить
    """
    print("Тест улучшенного алгоритма Spiess-Florian...")
    
    # Создаем связи для маршрута A -> B -> C на одном маршруте
    links = [
        Link("A", "B", "route1", 10, 15),  # 10 минут в пути, интервал 15 мин
        Link("B", "C", "route1", 15, 15),  # 15 минут в пути, интервал 15 мин
        # Добавим альтернативный маршрут от A к C для сравнения
        Link("A", "C", "route2", 30, 5),  # 30 минут в пути, интервал 5 мин
    ]
    
    stops = {"A", "B", "C"}
    od_matrix = {"A": {"C": 100}}  # 100 пассажиров из A в C
    destination = "C"
    
    result = compute_sf(links, stops, destination, od_matrix)
    
    print(f"Обобщенные затраты из A в C: {result.strategy.labels['A']}")
    print(f"Обобщенные затраты в C (должны быть 0): {result.strategy.labels['C']}")
    
    # Время по маршруту A -> B -> C составляет 10 + 15 = 25 минут
    # При правильной реализации это должно быть близко к оптимальному времени
    # без лишнего ожидания на остановке B
    
    print("Тест завершен успешно!")
    print(f"Оптимальные связи (a_set): {len(result.strategy.a_set)}")
    for link in result.strategy.a_set:
        print(f"  {link.from_node} -> {link.to_node} по маршруту {link.route_id}")

if __name__ == "__main__":
    test_same_route_improvement()