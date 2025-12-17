from utils import *
import math
from scipy.stats import norm

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
    u = {stop: 1.0 if stop == destination else 0.0 for stop in all_stops} # теперь это вероятности, а не стоимости
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
    stop_times, active_trips, all_stops = parse_gtfs_limited(directory, limit)
    all_links = calculate_links(stop_times, active_trips, all_stops)
    all_links = calculate_headways(stop_times, active_trips, all_links)

    return all_links, all_stops

if __name__ == "__main__":
    directory = "improved-gtfs-moscow-official"
    all_links, all_stops = parse_gtfs(directory)
    od_matrix = { "100457-8017": { "100457-1002179": 1000 } }
    destination = "100457-1002179"
    result = compute_sf_with_lateness_prob(all_links, all_stops, destination, od_matrix)