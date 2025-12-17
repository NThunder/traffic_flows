from gtfs_utils import PriorityQueue, parse_gtfs_limited
import math
import csv
from datetime import datetime
import os
import numpy as np
from scipy.stats import norm
import random
from tqdm import tqdm

class Link:
    def __init__(self, from_node, to_node, route_id, mean_travel_time, std_travel_time, headway):
        self.from_node = from_node
        self.to_node = to_node
        self.route_id = route_id
        self.mean_travel_time = mean_travel_time  # среднее время в пути
        self.std_travel_time = std_travel_time    # стандартное отклонение времени в пути
        self.headway = headway  # интервал движения

class Strategy:
    def __init__(self, labels, freqs, a_set):
        self.labels = labels  # теперь это вероятности, а не стоимости
        self.freqs = freqs
        self.a_set = a_set

class Volumes:
    def __init__(self, links, nodes):
        self.links = links
        self.nodes = nodes

class SFResult:
    def __init__(self, strategy, volumes):
        self.strategy = strategy
        self.volumes = volumes

ALPHA = 1.0
INFINITE_FREQUENCY = 999999.0
MATH_INF = float('inf')
VERBOSE = False

def calculate_lateness_probability(mean_time, std_time, arrival_deadline):
    """
    Рассчитывает вероятность опоздания для заданного времени в пути
    
    Параметры:
    - mean_time: среднее время в пути
    - std_time: стандартное отклонение времени в пути
    - arrival_deadline: максимально допустимое время прибытия (относительно начала поездки)
    
    Возвращает:
    - вероятность НЕ опоздания (вероятность прибытия вовремя)
    """
    if std_time <= 0:
        # Если нет вариации, просто проверяем, укладываемся ли в дедлайн
        return 1.0 if mean_time <= arrival_deadline else 0.0
    
    # Вероятность прибытия вовремя (CDF нормального распределения в точке arrival_deadline)
    prob_on_time = norm.cdf(arrival_deadline, loc=mean_time, scale=std_time)
    return prob_on_time

def find_optimal_strategy_with_lateness_prob(all_links, all_stops, destination, arrival_deadline):
    """
    Модифицированный алгоритм Флориана, минимизирующий вероятность опоздания
    
    Параметры:
    - all_links: список всех связей в транспортной сети
    - all_stops: список всех остановок
    - destination: целевая остановка
    - arrival_deadline: максимально допустимое время прибытия (в минутах от начала поездки)
    """
    if VERBOSE:
        print("1.1 Initialization for lateness probability model")

    # Инициализация: вероятность прибытия вовремя из целевой остановки равна 1.0
    u = {stop: 1.0 if stop == destination else 0.0 for stop in all_stops}
    f = {stop: 0.0 for stop in all_stops}

    overline_a = []

    # Precompute links by ToNode
    links_by_to_node = {}
    for link in all_links:
        # Проверяем, что обе остановки существуют в all_stops
        if link.to_node in all_stops and link.from_node in all_stops:
            if link.to_node not in links_by_to_node:
                links_by_to_node[link.to_node] = []
            links_by_to_node[link.to_node].append(link)

    # Priority queue
    # Вместо u[link.to_node] + link.travel_cost, мы будем использовать вероятность прибытия вовремя
    pq = PriorityQueue()
    for link in all_links:
        # Проверяем, что узел существует в all_stops
        if link.to_node in all_stops:
            # Вероятность прибытия вовремя из начальной точки дуги
            # Это будет равно вероятности прибытия вовремя в конечную точку дуги, умноженной на вероятность пройти эту дугу вовремя
            # Но для начальной инициализации используем упрощенный подход
            prob = calculate_lateness_probability(link.mean_travel_time, link.std_travel_time, arrival_deadline)
            # Мы максимизируем вероятность, поэтому используем отрицательное значение для min-heap
            pq.push(link, -prob)

    iteration = 0
    max_iterations = 10000  # защита от бесконечного цикла

    while iteration < max_iterations:
        link, neg_priority = pq.pop()
        if link is None:
            break
            
        priority = -neg_priority  # восстанавливаем исходную вероятность
        
        a = link
        i = a.from_node  # начальная остановка дуги
        j = a.to_node    # конечная остановка дуги

        # Проверяем, что обе остановки существуют в all_stops
        if i not in all_stops or j not in all_stops:
            continue

        # Рассчитываем вероятность прибытия вовремя из остановки i через дугу a
        # Это зависит от:
        # 1. Вероятности прибытия вовремя из остановки j (u[j])
        # 2. Вероятности успешно пройти дугу a (включая ожидание и движение)
        
        # Сначала рассчитываем характеристики дуги с учетом ожидания
        waiting_mean = a.headway / 2.0 if a.headway > 0 else 0  # среднее время ожидания
        waiting_std = a.headway / math.sqrt(12) if a.headway > 0 else 0  # std для равномерного распределения
        
        # Общее время: ожидание + движение
        total_mean = waiting_mean + a.mean_travel_time
        total_std = math.sqrt(waiting_std**2 + a.std_travel_time**2)
        
        # Вероятность прибытия вовремя из j через дугу a
        prob_arrive_via_a = calculate_lateness_probability(total_mean, total_std, arrival_deadline)
        
        # Обновляем вероятность для узла i, если найден лучший путь
        new_u_i = max(u[i], u[j] * prob_arrive_via_a)
        
        if new_u_i > u[i]:
            if VERBOSE:
                print(f"Update: u[{i}] from {u[i]} to {new_u_i} via ({i}, {j})")

            u[i] = new_u_i
            
            # Обновляем частоту (в контексте вероятностей)
            freq = INFINITE_FREQUENCY if a.headway <= 0 else 1 / a.headway
            f[i] = freq if freq < INFINITE_FREQUENCY else 1.0 # адаптируем для вероятностной модели
            
            overline_a.append(a)

            # Обновляем приоритеты для дуг, входящих в узел i
            if i in links_by_to_node:
                for update_link in links_by_to_node[i]:  # update_link = (pred, i)
                    # Проверяем существование узлов
                    if update_link.to_node in all_stops and update_link.from_node in all_stops:
                        # Пересчитываем вероятность для дуги update_link
                        waiting_mean_upd = update_link.headway / 2.0 if update_link.headway > 0 else 0
                        waiting_std_upd = update_link.headway / math.sqrt(12) if update_link.headway > 0 else 0
                        total_mean_upd = waiting_mean_upd + update_link.mean_travel_time
                        total_std_upd = math.sqrt(waiting_std_upd**2 + update_link.std_travel_time**2)
                        
                        prob_upd = calculate_lateness_probability(total_mean_upd, total_std_upd, arrival_deadline)
                        pq.update(update_link, -u[i] * prob_upd)  # используем новое значение u[i]

        iteration += 1

    return Strategy(u, f, overline_a)

def assign_demand_with_lateness_prob(all_links, all_stops, optimal_strategy, od_matrix, destination):
    """
    Распределение спроса с использованием стратегии, основанной на вероятности опоздания
    """
    # Сортируем a_set по убыванию вероятности (вместо возрастания стоимости)
    optimal_strategy.a_set = sorted(
        optimal_strategy.a_set, 
        key=lambda a: -(optimal_strategy.labels[a.to_node]),  # используем вероятности, а не стоимости
        reverse=True
    )

    node_volumes = {stop: 0.0 for stop in all_stops}
    for origin in od_matrix:
        if destination in od_matrix[origin]:
            node_volumes[origin] += od_matrix[origin][destination]
            node_volumes[destination] += od_matrix[origin][destination]
    node_volumes[destination] *= -1 # Как в оригинале

    # Инициализация объемов для связей
    volumes_links = {}
    for link in all_links:
        if link.from_node not in volumes_links:
            volumes_links[link.from_node] = {}
        volumes_links[link.from_node][link.to_node] = 0.0

    for a in optimal_strategy.a_set:
        freq = INFINITE_FREQUENCY if a.headway <= 0 else 1 / a.headway
        if optimal_strategy.freqs[a.from_node] == 0:
            va = 0.0
        else:
            va = (freq / optimal_strategy.freqs[a.from_node]) * node_volumes[a.from_node]
        if VERBOSE:
            print(f"Assigning demand for link: ({a.from_node}, {a.to_node})")
            print(f"  v_({a.from_node}, {a.to_node}) = {va}")
            print(f"  V_{a.to_node} += {va}")
        volumes_links[a.from_node][a.to_node] = va
        node_volumes[a.to_node] += va

    if VERBOSE:
        print("Final node volumes:")
        for k in node_volumes:
            print(f"  V_{k} = {node_volumes[k]}")

    return Volumes(volumes_links, node_volumes)

def compute_sf_with_lateness_prob(all_links, all_stops, destination, od_matrix, arrival_deadline):
    """
    Вычисление стратегии с учетом вероятности опоздания
    """
    ops = find_optimal_strategy_with_lateness_prob(all_links, all_stops, destination, arrival_deadline)
    volumes = assign_demand_with_lateness_prob(all_links, all_stops, ops, od_matrix, destination)
    return SFResult(ops, volumes)

def convert_time(time_str):
    """Преобразование времени из GTFS формата"""
    hours_converted = int(time_str[:2]) % 24
    return "{:02d}:".format(hours_converted) + time_str[3:]

def parse_gtfs(directory, limit=10000):
    """Парсинг GTFS данных с ограничением количества записей"""
    # Read files
    stops_path = os.path.join(directory, 'stops.txt')
    stop_times_path = os.path.join(directory, 'stop_times.txt')
    trips_path = os.path.join(directory, 'trips.txt')
    routes_path = os.path.join(directory, 'routes.txt')
    calendar_path = os.path.join(directory, 'calendar.txt')

    # Read stops
    all_stops = set()
    with open(stops_path, 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(tqdm(reader, desc="Reading stops", total=min(limit, 10105))):
            if i >= limit:
                break
            all_stops.add(row['stop_id'])

    # Read routes, trips, calendar to determine active services (for Dec 17, 2025 - Wednesday)
    # Assume start_date, end_date in YYYYMMDD, wednesday=1
    active_services = set()
    date_str = '20251217'  # YYYYMMDD for Dec 17, 2025
    weekday = 'wednesday'
    with open(calendar_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            start = row['start_date']
            end = row['end_date']
            if start <= date_str <= end and row[weekday] == '1':
                active_services.add(row['service_id'])

    # Filter trips by active services
    active_trips = {}
    with open(trips_path, 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(tqdm(reader, desc="Reading trips", total=min(limit, 25000))):
            if i >= limit:
                break
            if row['service_id'] in active_services:
                active_trips[row['trip_id']] = row['route_id']

    # Read stop_times, build links
    stop_times = {}
    with open(stop_times_path, 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(tqdm(reader, desc="Reading stop_times", total=min(limit, 2660216))):
            if i >= limit:
                break
            trip_id = row['trip_id']
            if trip_id not in active_trips:
                continue
            if trip_id not in stop_times:
                stop_times[trip_id] = []
            stop_times[trip_id].append(row)

    all_links = []
    for trip_id, times in tqdm(stop_times.items(), desc="Creating links"):
        times.sort(key=lambda x: int(x['stop_sequence']))
        route_id = active_trips[trip_id]
        for idx in range(len(times) - 1):
            current = times[idx]
            next_stop = times[idx + 1]
            from_node = current['stop_id']
            to_node = next_stop['stop_id']
            
            # Проверяем, что обе остановки присутствуют в all_stops
            if from_node not in all_stops or to_node not in all_stops:
                continue
                
            # Parse times HH:MM:SS to minutes
            dep_time = datetime.strptime(convert_time(current['departure_time']), '%H:%M:%S')
            arr_time = datetime.strptime(convert_time(next_stop['arrival_time']), '%H:%M:%S')
            mean_travel_time = (arr_time - dep_time).total_seconds() / 60.0  # minutes

            # Headway: Need to calculate per route at from_node
            headway = 0.0  # Set actual later

            # В реальной реализации нужно рассчитать std_travel_time на основе исторических данных
            # Для примера используем фиксированное значение
            std_travel_time = mean_travel_time * 0.2  # 20% от среднего времени

            link = Link(from_node, to_node, route_id, mean_travel_time, std_travel_time, headway)
            all_links.append(link)

    # Calculate headways: For each route, stop, collect departure times, sort, avg diff
    departures = {}  # (route_id, stop_id) -> list of dep_times in seconds
    for trip_id, times in tqdm(stop_times.items(), desc="Processing trips for headways"):
        route_id = active_trips[trip_id]
        for st in times:
            stop_id = st['stop_id']
            key = (route_id, stop_id)
            if key not in departures:
                departures[key] = []
            dep_time = datetime.strptime(convert_time(st['departure_time']), '%H:%M:%S')
            seconds = dep_time.hour * 3600 + dep_time.minute * 60 + dep_time.second
            departures[key].append(seconds)

    for key in tqdm(departures.keys(), desc="Calculating headways"):
        deps = sorted(departures[key])
        if len(deps) > 1:
            diffs = [deps[i+1] - deps[i] for i in range(len(deps)-1)]
            avg_headway = sum(diffs) / len(diffs) / 60.0  # minutes
            departures[key] = avg_headway
        else:
            departures[key] = 0.0  # or infinite

    # Assign headways to links (headway at from_node for route)
    for link in tqdm(all_links, desc="Assigning headways"):
        key = (link.route_id, link.from_node)
        link.headway = departures.get(key, 0.0)

    return all_links, all_stops

# Пример использования с нашими тестовыми данными
def parse_sample_data():
    """Парсинг наших тестовых данных"""
    all_stops = {'A', 'B', 'C', 'D', 'E'}
    
    # Создаем связи на основе stop_times.csv
    links_data = [
        # Маршрут 1: A -> B -> C
        ('A', 'B', '1', 10, 2, 30),   # 08:00:00 -> 08:10:00, headway 30 мин
        ('B', 'C', '1', 15, 3, 30),   # 08:10:00 -> 08:25:00
        ('A', 'B', '1', 10, 2, 30),   # 08:30:00 -> 08:40:00
        ('B', 'C', '1', 15, 3, 30),   # 08:40:00 -> 08:55:00
        
        # Маршрут 2: B -> D
        ('B', 'D', '2', 15, 4, 30),   # 08:05:00 -> 08:20:00
        ('B', 'D', '2', 15, 4, 30),   # 08:35:00 -> 08:50:00
        
        # Маршрут 3: C -> E
        ('C', 'E', '3', 15, 2, 30),   # 08:15:00 -> 08:30:00
        ('C', 'E', '3', 15, 2, 30),   # 08:45:00 -> 09:00:00
        
        # Экспресс: A -> D
        ('A', 'D', '4', 20, 5, 60),   # 08:00:00 -> 08:20:00
    ]
    
    # Уникализируем дуги, усредняя параметры
    unique_links = {}
    for from_node, to_node, route_id, mean_time, std_time, headway in links_data:
        key = (from_node, to_node, route_id)
        if key not in unique_links:
            unique_links[key] = {
                'mean_time': [],
                'std_time': [],
                'headway': headway
            }
        unique_links[key]['mean_time'].append(mean_time)
        unique_links[key]['std_time'].append(std_time)
    
    all_links = []
    for (from_node, to_node, route_id), data in unique_links.items():
        mean_time = sum(data['mean_time']) / len(data['mean_time'])
        std_time = sum(data['std_time']) / len(data['std_time'])
        headway = data['headway']
        link = Link(from_node, to_node, route_id, mean_time, std_time, headway)
        all_links.append(link)
    
    return all_links, all_stops

# Добавим функцию для запуска сравнения двух алгоритмов
def compare_algorithms():
    """
    Функция для сравнения оригинального алгоритма Флориана и модифицированного
    """
    print("Сравнение оригинального алгоритма Флориана и алгоритма с учетом вероятности опоздания")
    
    # Используем наши тестовые данные
    all_links, all_stops = parse_sample_data()
    
    # Параметры для тестирования
    destination = 'C'
    od_matrix = {'A': {'C': 1000}}  # 1000 пассажиров из A в C
    arrival_deadline = 25  # дедлайн в 25 минут
    
    # Вычисляем результаты с помощью модифицированного алгоритма
    result_lateness_prob = compute_sf_with_lateness_prob(
        all_links, all_stops, destination, od_matrix, arrival_deadline
    )
    
    print(f"Результаты модифицированного алгоритма (вероятность опоздания):")
    print(f"Вероятности прибытия вовремя: {result_lateness_prob.strategy.labels}")
    print(f"Объемы на узлах: {result_lateness_prob.volumes.nodes}")
    
    # Теперь импортируем и используем оригинальный алгоритм для сравнения
    import sys
    sys.path.append('.')
    from florian import compute_sf, Link as OriginalLink
    
    # Преобразуем наши данные для оригинального алгоритма
    original_links = [
        OriginalLink(link.from_node, link.to_node, link.route_id, link.mean_travel_time, link.headway)
        for link in all_links
    ]
    
    original_result = compute_sf(original_links, all_stops, destination, od_matrix)
    
    print(f"\nРезультаты оригинального алгоритма Флориана:")
    print(f"Обобщенные затраты: {original_result.strategy.labels}")
    print(f"Объемы на узлах: {original_result.volumes.nodes}")
    
    return result_lateness_prob, original_result

if __name__ == "__main__":
    compare_algorithms()