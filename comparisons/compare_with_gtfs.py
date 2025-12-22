import sys
import matplotlib.pyplot as plt

sys.path.append('.')

from algos.florian import compute_sf_improved as compute_sf_original
from algos.time_arrived_florian import compute_sf_improved as compute_sf_with_time_arrived
from utils import parse_gtfs_limited, calculate_links, calculate_headways, get_all_origins_reaching_destination
from comparisons.bus_route_visualization import find_bus_route, create_bus_route_visualization

def run_comparison_with_gtfs(limit=10000):
    """
    Функция для сравнения оригинального алгоритма Флориана и модифицированного
    с использованием GTFS-данных с ограничением
    """
    print(f"Сравнение оригинального алгоритма Флориана и алгоритма с учетом вероятности опоздания")
    print(f"Используется ограничение на {limit} записей из каждого файла GTFS")
    
    # Используем ограниченный парсинг GTFS
    directory = "improved-gtfs-moscow-official"
    
    # Парсим GTFS с ограничением
    stop_times, active_trips, all_stops, stop_names, route_names = parse_gtfs_limited(directory, limit=limit)

    all_links = calculate_links(stop_times, active_trips, all_stops)
    
    # Рассчитываем интервалы
    all_links = calculate_headways(stop_times, active_trips, all_links)
    
    # Создаем словарь интервалов из модифицированных связей
    departures = {}
    for link in all_links:
        key = (link.route_id, link.from_node)
        departures[key] = link.headway

    origin, destination = find_bus_route('с962', active_trips, stop_times, all_stops, route_names, all_links)
    
    arrival_deadline = 45  # дедлайн в 45 минут

    origins_reaching_dest = get_all_origins_reaching_destination(all_links, destination)

    print(f"Найдено {len(origins_reaching_dest)} остановок, из которых можно доехать до {destination}")

    od_matrix = {}
    for origin1 in origins_reaching_dest:
        if origin1 != destination:
            demand = 500 # random.uniform(50.0, 500.0)
            od_matrix[origin1] = {destination: demand}
    
    print(f"Тестирование на маршруте: {origin} -> {destination}")
    print(f"Количество остановок: {len(all_stops)}")
    print(f"Количество связей (original): {len(all_links)}")

    print("Вычисление результатов с оригинальным алгоритмом...")
    original_result = compute_sf_original(all_links, all_stops, destination, od_matrix)
    
    print(f"\nРезультаты оригинального алгоритма Флориана:")
    print(f"Обобщенные затраты из {origin}: {original_result.strategy.labels.get(origin, 'N/A')}")
    print(f"Обобщенные затраты в целевом узле: {original_result.strategy.labels.get(destination, 'N/A')}")
    
    print("Вычисление результатов с модифицированным алгоритмом...")
    result_time_arrived = compute_sf_with_time_arrived(
        all_links, all_stops, destination, od_matrix, arrival_deadline
    )
    
    print(f"\nРезультаты модифицированного алгоритма:")
    print(f"Вероятность прибытия вовремя из {origin}: {result_time_arrived.strategy.labels.get(origin, 'N/A')}")
    print(f"Вероятность прибытия вовремя в целевой узел: {result_time_arrived.strategy.labels.get(destination, 'N/A')}")
    
    # Сравниваем стратегии
    print(f"\nСравнение стратегий:")
    print(f"Оригинальный алгоритм - минимальные затраты из {origin}: {original_result.strategy.labels.get(origin, 'N/A')}")
    print(f"Новый алгоритм - вероятность прибытия вовремя из {origin}: {result_time_arrived.strategy.labels.get(origin, 'N/A')}")
    
    # Создаем визуализацию
    create_bus_route_visualization(original_result, result_time_arrived, all_stops, origin, destination, stop_names, route_names)
    
    return original_result, result_time_arrived

def run_extended_comparison_with_gtfs(limit=5000):
    """
    Расширенное сравнение с различными временными дедлайнами на GTFS-данных
    """
    
    # Используем ограниченный парсинг GTFS
    directory = "improved-gtfs-moscow-official"
    
    # Парсим GTFS с ограничением
    stop_times, active_trips, all_stops, stop_names, route_names = parse_gtfs_limited(directory, limit=limit)
    
    all_links = calculate_links(stop_times, active_trips, all_stops)

    # Рассчитываем интервалы
    all_links = calculate_headways(stop_times, active_trips, all_links)
    
    # Создаем словарь интервалов из модифицированных связей
    departures = {}
    for link in all_links:
        key = (link.route_id, link.from_node)
        departures[key] = link.headway

    origin, destination = find_bus_route('с962', active_trips, stop_times, all_stops, route_names, all_links)

    origins_reaching_dest = get_all_origins_reaching_destination(all_links, destination)

    print(f"Найдено {len(origins_reaching_dest)} остановок, из которых можно доехать до {destination}")

    od_matrix = {}
    for origin in origins_reaching_dest:
        if origin != destination:
            demand = 500 # random.uniform(50.0, 500.0)
            od_matrix[origin] = {destination: demand}
    
    # Тестируем с разными временными дедлайнами
    deadlines = [20, 30, 45, 60, 75]
    
    print("Сравнение при разных временных дедлайнах:")
    print("Дедлайн (мин) | Вероятность успеха (новый) | Затраты (оригинал)")
    print("-" * 60)
    
    results = []
    
    for deadline in deadlines:
        print(f"Обработка дедлайна: {deadline} минут")
        
        # Вычисляем результаты с помощью модифицированного алгоритма
        prob_result = compute_sf_with_time_arrived(
            all_links, all_stops, destination, od_matrix, deadline
        )
        
        # Вычисляем результаты с помощью оригинального алгоритма
        original_result = compute_sf_original(all_links, all_stops, destination, od_matrix)
        
        prob_success = prob_result.strategy.labels.get(origin, 0)
        original_cost = original_result.strategy.labels.get(origin, 0)
        
        # Обработка случая, когда значения могут быть кортежами или другими типами
        if hasattr(prob_success, '__len__') and not isinstance(prob_success, str):
            prob_success = prob_success[0] if len(prob_success) > 0 else 0
        if hasattr(original_cost, '__len__') and not isinstance(original_cost, str):
            original_cost = original_cost[0] if len(original_cost) > 0 else 0
        
        print(f"{deadline:11d} | {prob_success:23.4f} | {original_cost:16.4f}")
        
        results.append((deadline, prob_success, original_cost))
    
    # Визуализация зависимости
    if results:
        deadlines_vals, prob_vals, cost_vals = zip(*results)
        
        plt.figure(figsize=(12, 5))
        
        plt.subplot(1, 2, 1)
        plt.plot(deadlines_vals, prob_vals, 'b-o', label='Вероятность прибытия вовремя')
        plt.xlabel('Временной дедлайн (мин)')
        plt.ylabel('Вероятность')
        plt.title('Зависимость вероятности успеха от дедлайна')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.subplot(1, 2, 2)
        plt.plot(deadlines_vals, cost_vals, 'r-s', label='Обобщенные затраты')
        plt.xlabel('Временной дедлайн (мин)')
        plt.ylabel('Затраты')
        plt.title('Зависимость затрат от дедлайна')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.tight_layout()
        plt.savefig('gtfs_deadline_comparison.png', dpi=300, bbox_inches='tight')
        print(f"\nГрафик зависимости от дедлайна сохранен в файл 'gtfs_deadline_comparison.png'")
        plt.show()


if __name__ == "__main__":
    # Выполняем основное сравнение с GTFS-данными
    original_result, prob_result = run_comparison_with_gtfs(limit=100000)
    
    # Выполняем расширенное сравнение
    # run_extended_comparison_with_gtfs(limit=500)
    
    print("\nСравнение завершено.")