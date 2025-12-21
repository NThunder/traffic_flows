import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from datetime import datetime

# Добавляем текущую директорию в путь для импорта
sys.path.append('.')

from algos.florian import compute_sf, Link as OriginalLink, parse_gtfs as original_parse_gtfs
from algos.time_arrived_florian import compute_sf as compute_sf_with_time_arrived, Link as ProbLink, parse_gtfs as prob_parse_gtfs
from utils import parse_gtfs_limited, calculate_links, calculate_headways, find_connected_od_pair_with_min_hops, find_shortest_route_pair


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
    
    # Рассчитываем интервалы
    temp_links = calculate_headways(stop_times, active_trips, [], stop_names, route_names)
    
    # Создаем словарь интервалов из модифицированных связей
    departures = {}
    for link in temp_links:
        key = (link.route_id, link.from_node)
        departures[key] = link.headway
    
    # all_links = calculate_links(stop_times, active_trips, all_stops)
    
    # Создаем связи для оригинального алгоритма
    print("Создание связей для оригинального алгоритма...")
    original_links = []
    for trip_id, times in tqdm(stop_times.items(), desc="Creating original links"):
        times.sort(key=lambda x: int(x['stop_sequence']))
        route_id = active_trips[trip_id]
        for idx in range(len(times) - 1):
            current = times[idx]
            next_stop = times[idx + 1]
            from_node = current['stop_id']
            to_node = next_stop['stop_id']
            # Parse times HH:MM:SS to minutes
            dep_time = datetime.strptime(convert_time(current['departure_time']), '%H:%M:%S')
            arr_time = datetime.strptime(convert_time(next_stop['arrival_time']), '%H:%M:%S')
            travel_cost = (arr_time - dep_time).total_seconds() / 60.0  # minutes

            # Headway: Use calculated headway
            headway = departures.get((route_id, from_node), 0.0)

            link = OriginalLink(from_node, to_node, route_id, travel_cost, headway)
            original_links.append(link)

    # Создаем связи для вероятностного алгоритма
    print("Создание связей для вероятностного алгоритма...")
    prob_links = []
    for trip_id, times in tqdm(stop_times.items(), desc="Creating prob links"):
        times.sort(key=lambda x: int(x['stop_sequence']))
        route_id = active_trips[trip_id]
        for idx in range(len(times) - 1):
            current = times[idx]
            next_stop = times[idx + 1]
            from_node = current['stop_id']
            to_node = next_stop['stop_id']
            # Parse times HH:MM:SS to minutes
            dep_time = datetime.strptime(convert_time(current['departure_time']), '%H:%M:%S')
            arr_time = datetime.strptime(convert_time(next_stop['arrival_time']), '%H:%M:%S')
            mean_travel_time = (arr_time - dep_time).total_seconds() / 60.0  # minutes

            # Headway: Use calculated headway
            headway = departures.get((route_id, from_node), 0.0)

            # В реальной реализации нужно рассчитать std_travel_time на основе исторических данных
            # Для примера используем фиксированное значение
            std_travel_time = mean_travel_time * 0.2  # 20% от среднего времени

            link = ProbLink(from_node, to_node, route_id, mean_travel_time, headway, mean_travel_time, std_travel_time)
            prob_links.append(link)

    # Параметры для тестирования
    # Используем функцию из utils для нахождения пары с коротким маршрутом (до 10 остановок)
    origin, destination = find_shortest_route_pair(original_links, max_stops=10)
    
    # Если не найдена подходящая пара, используем первую и вторую остановку
    if origin is None or destination is None:
        stops_list = list(all_stops)
        if len(stops_list) < 2:
            print("Недостаточно остановок для тестирования")
            return None, None
        destination = stops_list[0]
        origin = stops_list[1] if len(stops_list) > 1 else stops_list[0]
    else:
        print(f"Найдена пара с маршрутом длиной до 10 остановок: {origin} -> {destination}")
    
    # Проверяем, что origin и destination существуют в all_stops
    if origin not in all_stops:
        origin = list(all_stops)[0]
    if destination not in all_stops:
        destination = list(all_stops)[1] if len(all_stops) > 1 else list(all_stops)[0]
    od_matrix = {origin: {destination: 1000}}  # 1000 пассажиров из origin в destination
    arrival_deadline = 45  # дедлайн в 45 минут
    
    print(f"Тестирование на маршруте: {origin} -> {destination}")
    print(f"Количество остановок: {len(all_stops)}")
    print(f"Количество связей (original): {len(original_links)}")
    print(f"Количество связей (prob): {len(prob_links)}")
    
    # Вычисляем результаты с помощью модифицированного алгоритма
    print("Вычисление результатов с вероятностным алгоритмом...")
    result_lateness_prob = compute_sf_with_time_arrived(
        prob_links, all_stops, destination, od_matrix, arrival_deadline
    )
    
    print(f"\nРезультаты модифицированного алгоритма (вероятность опоздания):")
    print(f"Вероятность прибытия вовремя из {origin}: {result_lateness_prob.strategy.labels.get(origin, 'N/A')}")
    print(f"Вероятность прибытия вовремя в целевой узел: {result_lateness_prob.strategy.labels.get(destination, 'N/A')}")
    
    # Вычисляем результаты с помощью оригинального алгоритма
    print("Вычисление результатов с оригинальным алгоритмом...")
    original_result = compute_sf(original_links, all_stops, destination, od_matrix)
    
    print(f"\nРезультаты оригинального алгоритма Флориана:")
    print(f"Обобщенные затраты из {origin}: {original_result.strategy.labels.get(origin, 'N/A')}")
    print(f"Обобщенные затраты в целевом узле: {original_result.strategy.labels.get(destination, 'N/A')}")
    
    # Сравниваем стратегии
    print(f"\nСравнение стратегий:")
    print(f"Оригинальный алгоритм - минимальные затраты из {origin}: {original_result.strategy.labels.get(origin, 'N/A')}")
    print(f"Новый алгоритм - вероятность прибытия вовремя из {origin}: {result_lateness_prob.strategy.labels.get(origin, 'N/A')}")
    
    # Создаем визуализацию
    create_comparison_visualization(original_result, result_lateness_prob, all_stops, origin, destination, stop_names, route_names)
    
    return original_result, result_lateness_prob

def convert_time(time_str):
    """Преобразование времени из GTFS формата (копия из других модулей)"""
    hours_converted = int(time_str[:2]) % 24
    return "{:02d}:".format(hours_converted) + time_str[3:]

def create_comparison_visualization(original_result, prob_result, all_stops, origin, destination, stop_names=None, route_names=None):
    """
    Создает визуализацию сравнения двух алгоритмов - только объемы
    """
    # Для более короткого маршрута, попробуем найти маршрут с меньшим количеством остановок
    # Используем стратегию для определения остановок на маршруте
    from collections import defaultdict
    from utils import get_all_origins_reaching_destination
    
    # Построим список остановок в порядке следования из origin в destination
    # Используем a_set (множество рёбер оптимальной стратегии) для построения маршрута
    def get_path_stops(strategy, origin, destination):
        # Построим граф из рёбер в a_set
        graph = defaultdict(list)
        for link in strategy.a_set:
            graph[link.from_node].append((link.to_node, link))
        
        # Найдем путь от origin до destination
        visited = set()
        path = []
        
        def dfs(current, target, current_path):
            if current == target:
                return current_path + [current]
            
            if current in visited:
                return None
            
            visited.add(current)
            for next_node, link in graph[current]:
                result = dfs(next_node, target, current_path + [current])
                if result:
                    return result
            visited.remove(current)
            return None
        
        result_path = dfs(origin, destination, [])
        return result_path if result_path else [origin, destination]  # В крайнем случае, просто origin и destination
    
    # Получаем остановки вдоль маршрута
    path_stops_original = get_path_stops(original_result.strategy, origin, destination)
    path_stops_prob = get_path_stops(prob_result.strategy, origin, destination)
    
    # Используем более короткий маршрут из двух
    if len(path_stops_original) <= len(path_stops_prob) and len(path_stops_original) <= 10:
        stops_to_show = path_stops_original
    elif len(path_stops_prob) <= 10:
        stops_to_show = path_stops_prob
    else:
        # Если оба маршрута длиннее 10, используем активные остановки, но ограничиваем до 10
        active_stops = set()
        for stop, volume in original_result.volumes.nodes.items():
            if volume != 0:
                active_stops.add(stop)
        for stop, volume in prob_result.volumes.nodes.items():
            if volume != 0:
                active_stops.add(stop)
        
        # Включаем origin и destination
        displayed_stops = [origin]
        if destination != origin and len(displayed_stops) < 10:
            displayed_stops.append(destination)
        
        # Добавляем остальные активные остановки
        for stop in active_stops:
            if stop != origin and stop != destination and len(displayed_stops) < 10:
                displayed_stops.append(stop)
        
        stops_to_show = displayed_stops
    
    # Преобразуем ID остановок в их названия, если доступны
    if stop_names:
        stop_labels = [stop_names.get(stop, stop) for stop in stops_to_show]
    else:
        stop_labels = stops_to_show
    
    # Определяем, какие остановки являются origin или destination
    special_stops = []
    for stop in stops_to_show:
        if stop == origin and stop == destination:
            special_stops.append("origin & dest")
        elif stop == origin:
            special_stops.append("origin")
        elif stop == destination:
            special_stops.append("destination")
        else:
            special_stops.append("regular")
    
    # Создаем график - только сравнение объемов
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    
    # Получаем информацию о маршрутах для заголовка
    # Ищем уникальные route_id, участвующие в пути
    routes_used = set()
    for link in original_result.strategy.a_set:
        routes_used.add(link.route_id)
    for link in prob_result.strategy.a_set:
        routes_used.add(link.route_id)
    
    # Преобразуем route_id в русские названия маршрутов, если доступны
    if route_names:
        route_labels = [route_names.get(route_id, route_id) for route_id in routes_used]
        routes_str = ", ".join(route_labels[:5])  # Ограничиваем до 5 маршрутов в заголовке
        if len(route_labels) > 5:
            routes_str += f" и еще {len(route_labels) - 5} маршрутов"
    else:
        routes_str = ", ".join(list(routes_used)[:5])  # Ограничиваем до 5 маршрутов в заголовке
        if len(routes_used) > 5:
            routes_str += f" и еще {len(routes_used) - 5} маршрутов"
    
    # Сравнение объемов на узлах
    x = np.arange(len(stops_to_show))
    width = 0.35
    
    # Получаем объемы для каждой остановки
    original_volumes = []
    for stop in stops_to_show:
        value = original_result.volumes.nodes.get(stop, 0)
        # Если значение - массив, берем первое значение
        if hasattr(value, '__len__') and not isinstance(value, str):
            original_volumes.append(value[0] if len(value) > 0 else 0)
        else:
            original_volumes.append(value)
    
    prob_volumes = []
    for stop in stops_to_show:
        value = prob_result.volumes.nodes.get(stop, 0)
        # Если значение - массив, берем первое значение
        if hasattr(value, '__len__') and not isinstance(value, str):
            prob_volumes.append(value[0] if len(value) > 0 else 0)
        else:
            prob_volumes.append(value)
    
    # Используем цвета для различия алгоритмов
    bars1 = ax.bar(x - width/2, original_volumes, width, label='Оригинальный алгоритм', alpha=0.8, color='skyblue')
    bars2 = ax.bar(x + width/2, prob_volumes, width, label='Алгоритм с вероятностью опоздания', alpha=0.8, color='orange')
    
    ax.set_xlabel('Остановки')
    ax.set_ylabel('Объемы')
    ax.set_title(f'Сравнение объемов на узлах (Маршруты: {routes_str})')
    ax.set_xticks(x)
    ax.set_xticklabels(stop_labels, rotation=45, ha="right")
    ax.legend()
    
    # Добавляем легенду для обозначения типов остановок
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor='skyblue', label='Оригинальный алгоритм'),
                       Patch(facecolor='orange', label='Алгоритм с вероятностью опоздания')]
    
    # Также добавим информацию о том, какая остановка является начальной/конечной
    # Подписываем особым образом origin и destination
    for i, stop_type in enumerate(special_stops):
        if stop_type == "origin":
            ax.get_xticklabels()[i].set_weight('bold')
        elif stop_type == "destination":
            ax.get_xticklabels()[i].set_style('italic')
        elif stop_type == "origin & dest":
            ax.get_xticklabels()[i].set_weight('bold')
            ax.get_xticklabels()[i].set_style('italic')
    
    fig.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 0.95), ncol=2)
    
    plt.tight_layout(rect=[0, 0, 1, 0.93])  # Делаем место для верхней легенды
    plt.savefig('gtfs_comparison_results.png', dpi=300, bbox_inches='tight')
    print(f"\nГрафик сравнения объемов сохранен в файл 'gtfs_comparison_results.png'")
    plt.show()


def analyze_morning_rush_implications():
    """
    Анализирует, как новый подход может повлиять на моделирование утренних потоков
    """
    print("\n" + "="*70)
    print("АНАЛИЗ ВЛИЯНИЯ НОВОГО ПОДХОДА НА МОДЕЛИРОВАНИЕ УТРЕННИХ ПОТОКОВ")
    print("="*70)
    
    print("""
    Классический алгоритм Флориана минимизирует ожидаемые обобщенные затраты,
    включая время ожидания, время в пути и штрафы за пересадки. 
    
    Новый подход минимизирует вероятность опоздания, что особенно актуально
    для утренних поездок на работу/учебу, когда людям важно прибыть к определенному
    времени с высокой вероятностью.
    
    ОСНОВНЫЕ ОТЛИЧИЯ:
    
    1. Учет неопределенности:
       - Оригинальный: предполагает детерминированные времена
       - Новый: учитывает вариабельность времени в пути (дисперсию)
    
    2. Целевая функция:
       - Оригинальный: минимизация среднего времени
       - Новый: максимизация вероятности прибытия вовремя
    
    3. Поведение пассажиров:
       - Оригинальный: пассажиры выбирают маршрут с минимальными ожидаемыми затратами
       - Новый: пассажиры выбирают маршрут, который дает максимальную вероятность 
                прибытия до заданного времени
    
    ПРЕИМУЩЕСТВА НОВОГО ПОДХОДА ДЛЯ УТРЕННИХ ПОТОКОВ:
    
    - Более реалистичное моделирование поведения пассажиров, которые стремятся 
      избежать опоздания на работу/учебу
    - Учет вариабельности транспортных потоков в утренние часы
    - Возможность моделирования "безопасного" выбора маршрута, когда пассажиры 
      выбирают более надежный, но возможно более длинный маршрут, чтобы избежать риска опоздания
    - Учет не только среднего времени, но и надежности маршрута
    
    ПРИМЕР СЦЕНАРИЯ:
    Допустим, у пассажира есть выбор между:
    a) Быстрым, но ненадежным маршрутом (15 мин в среднем, но с высокой вариацией)
    b) Более медленным, но надежным маршрутом (20 мин, с низкой вариацией)
    
    Оригинальный алгоритм предпочтет вариант (a) из-за меньшего среднего времени.
    Новый алгоритм может выбрать вариант (b), если дедлайн близок и надежность важнее скорости.
    """)

def run_extended_comparison_with_gtfs(limit=5000):
    """
    Расширенное сравнение с различными временными дедлайнами на GTFS-данных
    """
    print("\n" + "="*70)
    print("РАСШИРЕННОЕ СРАВНЕНИЕ С РАЗЛИЧНЫМИ ВРЕМЕННЫМИ ДЕДЛАЙНАМИ (на GTFS-данных)")
    print("="*70)
    
    def convert_time(time_str):
        """Преобразование времени из GTFS формата"""
        hours_converted = int(time_str[:2]) % 24
        return "{:02d}:".format(hours_converted) + time_str[3:]
    
    # Используем ограниченный парсинг GTFS
    directory = "improved-gtfs-moscow-official"
    
    # Парсим GTFS с ограничением
    stop_times, active_trips, all_stops, stop_names, route_names = parse_gtfs_limited(directory, limit=limit)
    
    # Рассчитываем интервалы
    temp_links = calculate_headways(stop_times, active_trips, [], stop_names, route_names)
    
    # Создаем словарь интервалов из модифицированных связей
    departures = {}
    for link in temp_links:
        key = (link.route_id, link.from_node)
        departures[key] = link.headway
    
    # Создаем связи для оригинального алгоритма
    print("Создание связей для оригинального алгоритма...")
    original_links = []
    for trip_id, times in tqdm(stop_times.items(), desc="Creating original links"):
        times.sort(key=lambda x: int(x['stop_sequence']))
        route_id = active_trips[trip_id]
        for idx in range(len(times) - 1):
            current = times[idx]
            next_stop = times[idx + 1]
            from_node = current['stop_id']
            to_node = next_stop['stop_id']
            # Parse times HH:MM:SS to minutes
            dep_time = datetime.strptime(convert_time(current['departure_time']), '%H:%M:%S')
            arr_time = datetime.strptime(convert_time(next_stop['arrival_time']), '%H:%M:%S')
            travel_cost = (arr_time - dep_time).total_seconds() / 60.0  # minutes

            # Headway: Use calculated headway
            headway = departures.get((route_id, from_node), 0.0)

            link = OriginalLink(from_node, to_node, route_id, travel_cost, headway)
            original_links.append(link)

    # Создаем связи для вероятностного алгоритма
    print("Создание связей для вероятностного алгоритма...")
    prob_links = []
    for trip_id, times in tqdm(stop_times.items(), desc="Creating prob links"):
        times.sort(key=lambda x: int(x['stop_sequence']))
        route_id = active_trips[trip_id]
        for idx in range(len(times) - 1):
            current = times[idx]
            next_stop = times[idx + 1]
            from_node = current['stop_id']
            to_node = next_stop['stop_id']
            # Parse times HH:MM:SS to minutes
            dep_time = datetime.strptime(convert_time(current['departure_time']), '%H:%M:%S')
            arr_time = datetime.strptime(convert_time(next_stop['arrival_time']), '%H:%M:%S')
            mean_travel_time = (arr_time - dep_time).total_seconds() / 60.0  # minutes

            # Headway: Use calculated headway
            headway = departures.get((route_id, from_node), 0.0)

            # В реальной реализации нужно рассчитать std_travel_time на основе исторических данных
            # Для примера используем фиксированное значение
            std_travel_time = mean_travel_time * 0.2  # 20% от среднего времени

            link = ProbLink(from_node, to_node, route_id, mean_travel_time, headway, mean_travel_time, std_travel_time)
            prob_links.append(link)
    

    # Параметры для тестирования
    # Используем функцию из utils для нахождения пары с коротким маршрутом (до 10 остановок)
    origin, destination = find_shortest_route_pair(original_links, max_stops=10)
    
    # Если не найдена подходящая пара, используем первую и вторую остановку
    if origin is None or destination is None:
        stops_list = list(all_stops)
        if len(stops_list) < 2:
            print("Недостаточно остановок для тестирования")
            return
        destination = stops_list[0]
        origin = stops_list[1] if len(stops_list) > 1 else stops_list[0]
    else:
        print(f"Найдена пара с маршрутом длиной до 10 остановок: {origin} -> {destination}")
    
    # Проверяем, что origin и destination существуют в all_stops
    if origin not in all_stops:
        origin = list(all_stops)[0]
    if destination not in all_stops:
        destination = list(all_stops)[1] if len(all_stops) > 1 else list(all_stops)[0]
    od_matrix = {origin: {destination: 1000}}  # 1000 пассажиров из origin в destination
    
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
            prob_links, all_stops, destination, od_matrix, deadline
        )
        
        # Вычисляем результаты с помощью оригинального алгоритма
        original_result = compute_sf(original_links, all_stops, destination, od_matrix)
        
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
    original_result, prob_result = run_comparison_with_gtfs(limit=5000)
    
    # Выполняем расширенное сравнение
    run_extended_comparison_with_gtfs(limit=500)
    
    # Анализируем влияние на утренние потоки
    analyze_morning_rush_implications()
    
    print("\nСравнение завершено. Результаты визуализированы и проанализированы.")