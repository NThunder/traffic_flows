#!/usr/bin/env python3
"""
Тест для проверки работы с пересадками и ожиданием
"""
from utils import Link
from algos.florian import compute_sf, compute_sf_improved

def test_transfer_example():
    """
    Тест с примером пересадки:
    A -> B -> C (один маршрут, route1, интервал 15 мин)
    A -> C (другой маршрут, route2, интервал 5 мин)
    
    Пассажир из A в C.
    Вариант 1: A -> B -> C (20 минут в пути, но с ожиданием в A на 15/2=7.5 мин в среднем)
    Вариант 2: A -> C (30 минут в пути, но с ожиданием в A на 5/2=2.5 мин в среднем)
    
    В улучшенной версии: A -> B -> C не должен добавлять ожидание на B, 
    но должен учитывать ожидание в A для начала поездки.
    """
    print("Тест с пересадками...")
    
    # Создаем связи
    links = [
        Link("A", "B", "route1", 10, 15),  # 10 минут в пути, интервал 15 мин
        Link("B", "C", "route1", 10, 15),  # 10 минут в пути, интервал 15 мин
        Link("A", "C", "route2", 30, 5),   # 30 минут в пути, интервал 5 мин
    ]
    
    stops = {"A", "B", "C"}
    od_matrix = {"A": {"C": 100}}  # 100 пассажиров из A в C
    destination = "C"
    
    print("=== Тест оригинального алгоритма ===")
    result_orig = compute_sf(links, stops, destination, od_matrix)
    print(f"Обобщенные затраты из A в C: {result_orig.strategy.labels['A']}")
    print(f"Оптимальные связи:")
    for link in result_orig.strategy.a_set:
        print(f"  {link.from_node} -> {link.to_node} по маршруту {link.route_id}")
    
    print("\n=== Тест улучшенного алгоритма ===")
    from algos.florian_enhanced import compute_sf_enhanced
    result_improved = compute_sf_enhanced(links, stops, destination, od_matrix)
    print(f"Обобщенные затраты из A в C: {result_improved.strategy.labels['A']}")
    print(f"Оптимальные связи:")
    for link in result_improved.strategy.a_set:
        print(f"  {link.from_node} -> {link.to_node} по маршруту {link.route_id}")
    
    print("\n=== Анализ ===")
    print("Оригинальный алгоритм должен учитывать ожидание в A для обоих маршрутов")
    print("Улучшенный алгоритм должен учитывать ожидание в A, но не добавлять его между B и C")
    print("Так как B->C - это продолжение маршрута route1, а не пересадка")


def test_start_wait_example():
    """
    Простой тест: A -> B -> C на одном маршруте
    Пассажир начинает в A, значит должен ждать автобус route1
    """
    print("\n" + "="*50)
    print("Тест с ожиданием в начале поездки...")
    
    links = [
        Link("A", "B", "route1", 5, 10),  # 5 минут в пути, интервал 10 мин
        Link("B", "C", "route1", 5, 10),  # 5 минут в пути, интервал 10 мин
    ]
    
    stops = {"A", "B", "C"}
    od_matrix = {"A": {"C": 10}}
    destination = "C"
    
    print("=== Тест оригинального алгоритма ===")
    result_orig = compute_sf(links, stops, destination, od_matrix)
    print(f"Обобщенные затраты из A в C: {result_orig.strategy.labels['A']}")
    print(f"Оптимальные связи:")
    for link in result_orig.strategy.a_set:
        print(f"  {link.from_node} -> {link.to_node} по маршруту {link.route_id}")
    
    print("\n=== Тест улучшенного алгоритма ===")
    from algos.florian_enhanced import compute_sf_enhanced
    result_improved = compute_sf_enhanced(links, stops, destination, od_matrix)
    print(f"Обобщенные затраты из A в C: {result_improved.strategy.labels['A']}")
    print(f"Оптимальные связи:")
    for link in result_improved.strategy.a_set:
        print(f" {link.from_node} -> {link.to_node} по маршруту {link.route_id}")
    
    print("\n=== Ожидаемый результат ===")
    print("В узле A пассажир начинает поездку, значит должен подождать автобус route1 ~ 5 минут (10/2)")
    print("Затем 5 минут в пути до B, затем 5 минут в пути до C")
    print("Итого: 5 + 5 + 5 = 15 минут (примерно)")


if __name__ == "__main__":
    test_transfer_example()
    test_start_wait_example()